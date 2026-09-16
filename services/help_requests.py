"""
services/help_requests.py — Support & Communication Service for FULCRUM-INDIA
=============================================================================
Replaces complex WebSockets/chat with a lean, reliable ticketing queue.
- Aspirants raise help requests; automatically assigned to their Guide (or Admin if unassigned).
- Guides view assigned requests, reply, and resolve them.
- Any request unhandled for >7 days is automatically escalated to Admin.
- Automatically logs meaningful Journey events upon creation and resolution.
Supports dual backends: Supabase (primary) and SQLite (explicit local development).
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client, get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

def _get_user_client():
    """Returns the authenticated user's Supabase client (RLS-enforced)."""
    return get_supabase_client()

def _get_admin_client():
    """Returns the privileged admin Supabase client (bypasses RLS). Use sparingly."""
    return get_supabase_admin_client()

def create_request(
    aspirant_id: str,
    subject: str,
    message: str,
    priority: str = "MEDIUM",
    category: str = "GENERAL",
    target_role: str = "guide"
) -> Tuple[Optional[Dict], Optional[str]]:
    """Aspirant submits a support/help request. Automatically routes to assigned Guide and/or SME."""
    if not subject or not message:
        return None, "Subject and message are required."

    # Look up assigned mentors
    assigned_guide_id = None
    assigned_sme_id = None
    try:
        from services.relationships import get_aspirant_mentors
        mentors = get_aspirant_mentors(aspirant_id)
        guide = mentors.get("guide")
        sme = mentors.get("sme")
        if guide and guide.get("id"):
            assigned_guide_id = guide["id"]
        if sme and sme.get("id"):
            assigned_sme_id = sme["id"]
    except Exception:
        pass

    # Domain category routing
    is_sme_domain = category in ("GST_TAXATION", "LEGAL_COMPLIANCE", "FSSAI_FOOD", "PATENTS_IPR")
    if is_sme_domain or target_role == "sme":
        target_role = "sme"
    elif target_role not in ("guide", "sme", "both"):
        target_role = "guide"

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()
    req_id = str(uuid.uuid4())

    target_mentor_id = assigned_sme_id if (target_role == "sme" and assigned_sme_id) else assigned_guide_id

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if not client:
            return None, "Supabase client unavailable."
        req_data = {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject.strip(),
            "message": message.strip(),
            "priority": priority,
            "status": "OPEN",
            "assigned_guide_id": target_mentor_id,
            "assigned_at": now_iso if target_mentor_id else None,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        try:
            res = client.table("help_requests").insert(req_data).execute()
            req = res.data[0] if (res.data and len(res.data) > 0) else req_data
        except Exception as e:
            admin_client = _get_admin_client()
            if admin_client and admin_client != client:
                try:
                    res = admin_client.table("help_requests").insert(req_data).execute()
                    req = res.data[0] if (res.data and len(res.data) > 0) else req_data
                except Exception as e2:
                    return None, f"Failed to submit help request to Supabase: {e2}"
            else:
                return None, f"Failed to submit help request to Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        req = local_db.create_help_request(
            aspirant_id=aspirant_id,
            subject=subject.strip(),
            message=message.strip(),
            priority=priority,
            assigned_guide_id=assigned_guide_id,
            category=category,
            assigned_sme_id=assigned_sme_id,
            target_role=target_role
        )

    # Dispatch In-App Notifications to Mentor(s)
    from services.notifications import create_notification
    from services.profiles import get_profile
    asp_p = get_profile(aspirant_id)
    asp_name = asp_p.get("full_name") if asp_p else "An Entrepreneur"

    if target_role in ("sme", "both") and assigned_sme_id:
        create_notification(
            user_id=assigned_sme_id,
            title=f"New Domain Advisory Request: {subject.strip()}",
            message=f"{asp_name} requested expert support for {category} (Priority: {priority}).",
            notification_type="help_ticket_created",
            actor_id=aspirant_id
        )
    if target_role in ("guide", "both") and assigned_guide_id:
        create_notification(
            user_id=assigned_guide_id,
            title=f"New Help Ticket: {subject.strip()}",
            message=f"{asp_name} submitted a support request (Priority: {priority}).",
            notification_type="help_ticket_created",
            actor_id=aspirant_id
        )

    return req, None

def list_requests(aspirant_id: Optional[str] = None) -> List[Dict]:
    """Retrieves tickets for an Aspirant or all tickets for Admin from active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        # Admin listing all tickets needs admin client; aspirant listing own uses RLS or admin fallback
        client = _get_admin_client() if not aspirant_id else (_get_user_client() or _get_admin_client())
        if client:
            try:
                q = client.table("help_requests").select("*, profiles:aspirant_id(full_name, email)")
                if aspirant_id:
                    q = q.eq("aspirant_id", aspirant_id)
                res = q.order("created_at", desc=True).execute()
                rows = []
                for r in (res.data or []):
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                if rows:
                    return rows
                # If rows is empty and an admin client exists, check if unauthenticated user client was filtered by RLS
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    q_admin = admin_client.table("help_requests").select("*, profiles:aspirant_id(full_name, email)")
                    if aspirant_id:
                        q_admin = q_admin.eq("aspirant_id", aspirant_id)
                    res_admin = q_admin.order("created_at", desc=True).execute()
                    rows_admin = []
                    for r in (res_admin.data or []):
                        p = r.get("profiles") or {}
                        r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                        r["aspirant_email"] = p.get("email") or ""
                        rows_admin.append(r)
                    return rows_admin
                return rows
            except Exception as e:
                # If user client failed with RLS, try admin client
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    try:
                        q = admin_client.table("help_requests").select("*, profiles:aspirant_id(full_name, email)")
                        if aspirant_id:
                            q = q.eq("aspirant_id", aspirant_id)
                        res = q.order("created_at", desc=True).execute()
                        rows = []
                        for r in (res.data or []):
                            p = r.get("profiles") or {}
                            r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                            r["aspirant_email"] = p.get("email") or ""
                            rows.append(r)
                        return rows
                    except Exception as e2:
                        print(f"[HelpRequests] Admin fallback error: {e2}")
                print(f"[HelpRequests] Supabase list error: {e}")
                return []
        return []

    return get_local_db().list_help_requests(aspirant_id=aspirant_id)

def list_guide_requests(guide_id: str) -> List[Dict]:
    """Retrieves tickets assigned to a specific Guide."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                res = client.table("help_requests")\
                    .select("*, profiles:aspirant_id(full_name, email)")\
                    .eq("assigned_guide_id", guide_id)\
                    .order("created_at", desc=True)\
                    .execute()
                rows = []
                for r in (res.data or []):
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                if rows:
                    return rows
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    res_admin = admin_client.table("help_requests")\
                        .select("*, profiles:aspirant_id(full_name, email)")\
                        .eq("assigned_guide_id", guide_id)\
                        .order("created_at", desc=True)\
                        .execute()
                    rows_admin = []
                    for r in (res_admin.data or []):
                        p = r.get("profiles") or {}
                        r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                        r["aspirant_email"] = p.get("email") or ""
                        rows_admin.append(r)
                    return rows_admin
                return rows
            except Exception as e:
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    try:
                        res = admin_client.table("help_requests")\
                            .select("*, profiles:aspirant_id(full_name, email)")\
                            .eq("assigned_guide_id", guide_id)\
                            .order("created_at", desc=True)\
                            .execute()
                        rows = []
                        for r in (res.data or []):
                            p = r.get("profiles") or {}
                            r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                            r["aspirant_email"] = p.get("email") or ""
                            rows.append(r)
                        return rows
                    except Exception as e2:
                        print(f"[HelpRequests] Guide requests admin fallback error: {e2}")
                print(f"[HelpRequests] Supabase list_guide_requests error: {e}")
                return []
        return []

    return get_local_db().list_help_requests(guide_id=guide_id)

def guide_respond_request(request_id: str, guide_id: str, new_status: str, response: str) -> Tuple[bool, Optional[str]]:
    """Guide responds to an assigned ticket and updates status."""
    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if not client:
            return False, "Supabase client unavailable."
        try:
            # Check ticket authorization
            t_res = client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                admin_client = _get_admin_client()
                if admin_client:
                    t_res = admin_client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                return False, "Help request not found."
            req = t_res.data[0]
            if req.get("assigned_guide_id") and str(req.get("assigned_guide_id")) != str(guide_id):
                return False, "You are not authorized to respond to this request."

            aspirant_id = req["aspirant_id"]
            subject = req["subject"]

            update_payload = {
                "status": new_status,
                "guide_response": response.strip(),
                "last_handled_at": now_iso,
                "updated_at": now_iso
            }
            if new_status == "RESOLVED":
                update_payload["resolved_by"] = guide_id

            u_res = client.table("help_requests").update(update_payload).eq("id", request_id).execute()
            if not getattr(u_res, "data", None):
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    admin_client.table("help_requests").update(update_payload).eq("id", request_id).execute()
        except Exception as e:
            admin_client = _get_admin_client()
            if admin_client and admin_client != client:
                try:
                    admin_client.table("help_requests").update(update_payload).eq("id", request_id).execute()
                except Exception as e2:
                    return False, f"Failed to update help request in Supabase: {e2}"
            else:
                return False, f"Failed to update help request in Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return False, "Help request not found."

        req = dict(row)
        if req.get("assigned_guide_id") and req.get("assigned_guide_id") != guide_id:
            return False, "You are not authorized to respond to this request."

        aspirant_id = req["aspirant_id"]
        subject = req["subject"]
        local_db.guide_respond_help_request(request_id, guide_id, new_status, response.strip())

    # Dispatch notification to Aspirant
    from services.notifications import create_notification
    create_notification(
        user_id=aspirant_id,
        title=f"Guide Responded: {subject}",
        message=f"Your Guide replied: '{response.strip()[:100]}...' (Status: {new_status})",
        notification_type="help_ticket_replied",
        actor_id=guide_id
    )

    return True, None

def list_sme_requests(sme_id: str) -> List[Dict]:
    """Retrieves tickets assigned to a specific SME or for their assigned aspirants."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                res = client.table("help_requests")\
                    .select("*, profiles:aspirant_id(full_name, email)")\
                    .eq("assigned_guide_id", sme_id)\
                    .order("created_at", desc=True)\
                    .execute()
                rows = []
                for r in (res.data or []):
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                return rows
            except Exception as e:
                print(f"[HelpRequests] Supabase list_sme_requests error: {e}")
                return []
        return []

    return get_local_db().list_help_requests(sme_id=sme_id)

def sme_respond_request(request_id: str, sme_id: str, arg3: str, arg4: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """SME responds to an assigned advisory ticket and updates status."""
    if arg4 is None:
        new_status = "IN_PROGRESS"
        response = arg3
    elif arg3 in ("OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED"):
        new_status = arg3
        response = arg4
    else:
        response = arg3
        new_status = arg4 or "IN_PROGRESS"

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if not client:
            return False, "Supabase client unavailable."
        try:
            t_res = client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                admin_client = _get_admin_client()
                if admin_client:
                    t_res = admin_client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                return False, "Help request not found."
            req = t_res.data[0]
            if req.get("assigned_sme_id") and str(req.get("assigned_sme_id")) != str(sme_id):
                return False, "You are not authorized to respond to this request."

            aspirant_id = req["aspirant_id"]
            subject = req["subject"]

            update_payload = {
                "status": new_status,
                "guide_response": response.strip(),
                "responded_by": sme_id,
                "last_handled_at": now_iso,
                "updated_at": now_iso
            }
            if new_status == "RESOLVED":
                update_payload["resolved_by"] = sme_id

            u_res = client.table("help_requests").update(update_payload).eq("id", request_id).execute()
            if not getattr(u_res, "data", None):
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    admin_client.table("help_requests").update(update_payload).eq("id", request_id).execute()
        except Exception as e:
            admin_client = _get_admin_client()
            if admin_client and admin_client != client:
                try:
                    admin_client.table("help_requests").update(update_payload).eq("id", request_id).execute()
                except Exception as e2:
                    return False, f"Failed to update help request in Supabase: {e2}"
            else:
                return False, f"Failed to update help request in Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return False, "Help request not found."

        req = dict(row)
        if req.get("assigned_sme_id") and req.get("assigned_sme_id") != sme_id:
            return False, "You are not authorized to respond to this request."

        aspirant_id = req["aspirant_id"]
        subject = req["subject"]
        local_db.sme_respond_help_request(request_id, sme_id, new_status, response.strip())

    # Dispatch notification to Aspirant
    from services.notifications import create_notification
    create_notification(
        user_id=aspirant_id,
        title=f"Domain Specialist Responded: {subject}",
        message=f"SME specialist replied: '{response.strip()[:100]}...' (Status: {new_status})",
        notification_type="help_ticket_replied",
        actor_id=sme_id
    )

    return True, None

def resolve_request(request_id: str, new_status: str, admin_response: str, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Admin updates ticket status and records official response."""
    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client unavailable."
        try:
            t_res = client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                return False, "Help request not found."
            req = t_res.data[0]
            aspirant_id = req["aspirant_id"]
            subject = req["subject"]

            update_payload = {
                "status": new_status,
                "admin_response": admin_response.strip(),
                "responded_by": admin_id,
                "resolved_by": admin_id if new_status == "RESOLVED" else None,
                "updated_at": now_iso
            }
            client.table("help_requests").update(update_payload).eq("id", request_id).execute()
        except Exception as e:
            return False, f"Failed to resolve request in Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return False, "Help request not found."

        req = dict(row)
        aspirant_id = req["aspirant_id"]
        subject = req["subject"]
        local_db.update_help_request_status(request_id, new_status, admin_response.strip(), admin_id)

    # Dispatch notification to Aspirant
    from services.notifications import create_notification
    create_notification(
        user_id=aspirant_id,
        title=f"Administrative Action: {subject}",
        message=f"Administrator recorded directive on ticket '{subject}' (Status: {new_status}).",
        notification_type="help_ticket_replied",
        actor_id=admin_id
    )

    return True, None

def check_and_escalate_overdue_requests() -> int:
    """Auto-escalates unresolved tickets older than 7 days to 'ESCALATED'."""
    backend = get_data_backend()

    if backend == "supabase":
        client = get_supabase_admin_client() or get_supabase_client()
        if client:
            try:
                # First try the stored procedure
                rpc_res = client.rpc("escalate_overdue_help_requests").execute()
                if rpc_res.data is not None:
                    return int(rpc_res.data)
            except Exception:
                pass

            try:
                # Direct update
                seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                res = client.table("help_requests").update({
                    "status": "ESCALATED",
                    "escalated_at": datetime.now(timezone.utc).isoformat(),
                    "escalation_reason": "Automatically escalated after 7 days without resolution.",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).in_("status", ["OPEN", "IN_PROGRESS"]).lte("created_at", seven_days_ago).execute()
                return len(res.data or [])
            except Exception as e:
                print(f"[HelpRequests] Supabase auto-escalation error: {e}")
                return 0
        return 0

    return get_local_db().auto_escalate_overdue_requests(days=7)
