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

def _enrich_mentor_names(rows: List[Dict], client=None) -> List[Dict]:
    """Enriches consultation ticket rows with guide_name and sme_name from profiles if missing."""
    if not rows:
        return rows
    mentor_ids = set()
    for r in rows:
        if r.get("assigned_guide_id"):
            mentor_ids.add(r["assigned_guide_id"])
        if r.get("assigned_sme_id"):
            mentor_ids.add(r["assigned_sme_id"])
        if r.get("requester_id") and r.get("requester_role") in ("guide", "sme"):
            mentor_ids.add(r["requester_id"])

    valid_ids = []
    for mid in mentor_ids:
        s = str(mid)
        if len(s) == 36 and s.count("-") == 4:
            valid_ids.append(s)

    if not valid_ids:
        return rows

    try:
        admin_c = _get_admin_client() or client
        if admin_c:
            res = admin_c.table("profiles").select("id, full_name, role").in_("id", valid_ids).execute()
            name_map = {p["id"]: p.get("full_name") for p in (res.data or []) if p.get("full_name")}
            for r in rows:
                if not r.get("guide_name") and r.get("assigned_guide_id") in name_map:
                    r["guide_name"] = name_map[r["assigned_guide_id"]]
                if not r.get("sme_name") and r.get("assigned_sme_id") in name_map:
                    r["sme_name"] = name_map[r["assigned_sme_id"]]
                if r.get("requester_id") in name_map:
                    if r.get("requester_role") == "guide" and not r.get("guide_name"):
                        r["guide_name"] = name_map[r["requester_id"]]
                    elif r.get("requester_role") == "sme" and not r.get("sme_name"):
                        r["sme_name"] = name_map[r["requester_id"]]
    except Exception as e:
        print(f"[HelpRequests] Error enriching mentor names: {e}")
    return rows

def create_request(
    aspirant_id: str,
    subject: str,
    message: str,
    priority: str = "MEDIUM",
    category: str = "GENERAL",
    target_role: str = "guide",
    target_mentor_id: Optional[str] = None,
    category_detail: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """Aspirant submits a support/help request. Automatically routes to targeted or assigned Guide/SME."""
    if not subject or not message:
        return None, "Subject and message are required."

    # Look up assigned mentors
    assigned_guide_id = None
    assigned_sme_id = None
    all_smes = []
    try:
        from services.relationships import get_aspirant_mentors
        mentors = get_aspirant_mentors(aspirant_id)
        guide = mentors.get("guide")
        all_smes = mentors.get("smes", [])
        if not all_smes and mentors.get("sme"):
            all_smes = [mentors.get("sme")]
        if guide and guide.get("id"):
            assigned_guide_id = guide["id"]
        if all_smes:
            assigned_sme_id = all_smes[0]["id"]
    except Exception:
        pass

    # Targeted mentor routing
    if target_mentor_id:
        matching_sme = next((s for s in all_smes if s.get("id") == target_mentor_id), None)
        if matching_sme:
            target_role = "sme"
            actual_guide_id = None
            actual_sme_id = target_mentor_id
        elif assigned_guide_id and target_mentor_id == assigned_guide_id:
            target_role = "guide"
            actual_guide_id = target_mentor_id
            actual_sme_id = None
        else:
            if target_role == "sme":
                actual_guide_id = None
                actual_sme_id = target_mentor_id
            else:
                target_role = "guide"
                actual_guide_id = target_mentor_id
                actual_sme_id = None
    else:
        # Fallback category-based routing
        is_sme_domain = category in ("GST_TAXATION", "LEGAL_COMPLIANCE", "FSSAI_FOOD", "PATENTS_IPR")
        if is_sme_domain or target_role == "sme":
            target_role = "sme"
            actual_guide_id = None
            actual_sme_id = assigned_sme_id
        elif target_role == "both":
            actual_guide_id = assigned_guide_id
            actual_sme_id = assigned_sme_id
        else:
            target_role = "guide"
            actual_guide_id = assigned_guide_id
            actual_sme_id = None

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()
    req_id = str(uuid.uuid4())
    assigned_at = now_iso if (actual_guide_id or actual_sme_id) else None
    clean_cat_detail = category_detail.strip() if category_detail else None

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
            "assigned_guide_id": actual_guide_id,
            "assigned_sme_id": actual_sme_id,
            "category": category,
            "category_detail": clean_cat_detail,
            "target_role": target_role,
            "request_type": "aspirant_consultation",
            "assigned_at": assigned_at,
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
                    # If category_detail column is missing, retry without it
                    if "category_detail" in str(e2):
                        req_data.pop("category_detail", None)
                        try:
                            res = admin_client.table("help_requests").insert(req_data).execute()
                            req = res.data[0] if (res.data and len(res.data) > 0) else req_data
                        except Exception as e3:
                            return None, f"Failed to submit help request to Supabase: {e3}"
                    else:
                        return None, f"Failed to submit help request to Supabase: {e2}"
            else:
                if "category_detail" in str(e):
                    req_data.pop("category_detail", None)
                    try:
                        res = client.table("help_requests").insert(req_data).execute()
                        req = res.data[0] if (res.data and len(res.data) > 0) else req_data
                    except Exception as e3:
                        return None, f"Failed to submit help request to Supabase: {e3}"
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
            assigned_guide_id=actual_guide_id,
            category=category,
            category_detail=clean_cat_detail,
            assigned_sme_id=actual_sme_id,
            target_role=target_role
        )

    # Dispatch In-App Notifications strictly to the targeted Mentor
    from services.notifications import create_notification
    from services.profiles import get_profile
    asp_p = get_profile(aspirant_id)
    asp_name = asp_p.get("full_name") if asp_p else "An Entrepreneur"
    cat_label = clean_cat_detail if (category == "OTHERS" and clean_cat_detail) else category.replace("_", " ")

    if target_role in ("sme", "both") and actual_sme_id:
        create_notification(
            user_id=actual_sme_id,
            title=f"New Domain Advisory Request: {subject.strip()}",
            message=f"{asp_name} requested expert support for {cat_label} (Priority: {priority}).",
            notification_type="help_ticket_created",
            actor_id=aspirant_id
        )
    if target_role in ("guide", "both") and actual_guide_id:
        create_notification(
            user_id=actual_guide_id,
            title=f"New Help Ticket: {subject.strip()}",
            message=f"{asp_name} submitted a support request for {cat_label} (Priority: {priority}).",
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
                    if r.get("request_type") == "mentor_admin_query":
                        continue
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                if rows:
                    return _enrich_mentor_names(rows, client)
                # If rows is empty and an admin client exists, check if unauthenticated user client was filtered by RLS
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    q_admin = admin_client.table("help_requests").select("*, profiles:aspirant_id(full_name, email)")
                    if aspirant_id:
                        q_admin = q_admin.eq("aspirant_id", aspirant_id)
                    res_admin = q_admin.order("created_at", desc=True).execute()
                    rows_admin = []
                    for r in (res_admin.data or []):
                        if r.get("request_type") == "mentor_admin_query":
                            continue
                        p = r.get("profiles") or {}
                        r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                        r["aspirant_email"] = p.get("email") or ""
                        rows_admin.append(r)
                    return _enrich_mentor_names(rows_admin, admin_client)
                return _enrich_mentor_names(rows, client)
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
                            if r.get("request_type") == "mentor_admin_query":
                                continue
                            p = r.get("profiles") or {}
                            r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                            r["aspirant_email"] = p.get("email") or ""
                            rows.append(r)
                        return _enrich_mentor_names(rows, admin_client)
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
                    if r.get("request_type") == "mentor_admin_query":
                        continue
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                if rows:
                    return _enrich_mentor_names(rows, client)
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    res_admin = admin_client.table("help_requests")\
                        .select("*, profiles:aspirant_id(full_name, email)")\
                        .eq("assigned_guide_id", guide_id)\
                        .order("created_at", desc=True)\
                        .execute()
                    rows_admin = []
                    for r in (res_admin.data or []):
                        if r.get("request_type") == "mentor_admin_query":
                            continue
                        p = r.get("profiles") or {}
                        r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                        r["aspirant_email"] = p.get("email") or ""
                        rows_admin.append(r)
                    return _enrich_mentor_names(rows_admin, admin_client)
                return _enrich_mentor_names(rows, client)
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
                            if r.get("request_type") == "mentor_admin_query":
                                continue
                            p = r.get("profiles") or {}
                            r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                            r["aspirant_email"] = p.get("email") or ""
                            rows.append(r)
                        return _enrich_mentor_names(rows, admin_client)
                    except Exception as e2:
                        print(f"[HelpRequests] Guide requests admin fallback error: {e2}")
                print(f"[HelpRequests] Supabase list_guide_requests error: {e}")
                return []
        return []

    return get_local_db().list_help_requests(guide_id=guide_id)

def guide_respond_request(request_id: str, guide_id: str, new_status: str, response: str) -> Tuple[bool, Optional[str]]:
    """Guide responds to an assigned ticket and updates status."""
    # PART 7 — AUTHORIZATION: Verify caller is authorized
    try:
        import streamlit as st
        session_user = st.session_state.get("user")
        session_role = st.session_state.get("role")
        session_uid = st.session_state.get("user_id")
        if session_user and session_role not in ("admin", "guide"):
            return False, "Unauthorized: Only assigned Guides or Admins may respond to this consultation."
        if session_user and session_role == "guide" and str(session_uid) != str(guide_id):
            return False, "Unauthorized: You cannot respond on behalf of another Guide."
    except Exception:
        pass

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
                    .eq("assigned_sme_id", sme_id)\
                    .neq("request_type", "mentor_admin_query")\
                    .order("created_at", desc=True)\
                    .execute()
                rows = []
                for r in (res.data or []):
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                if rows:
                    return _enrich_mentor_names(rows, client)
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    res_admin = admin_client.table("help_requests")\
                        .select("*, profiles:aspirant_id(full_name, email)")\
                        .eq("assigned_sme_id", sme_id)\
                        .neq("request_type", "mentor_admin_query")\
                        .order("created_at", desc=True)\
                        .execute()
                    rows_admin = []
                    for r in (res_admin.data or []):
                        p = r.get("profiles") or {}
                        r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                        r["aspirant_email"] = p.get("email") or ""
                        rows_admin.append(r)
                    return _enrich_mentor_names(rows_admin, admin_client)
                return _enrich_mentor_names(rows, client)
            except Exception as e:
                admin_client = _get_admin_client()
                if admin_client and admin_client != client:
                    try:
                        res = admin_client.table("help_requests")\
                            .select("*, profiles:aspirant_id(full_name, email)")\
                            .eq("assigned_sme_id", sme_id)\
                            .neq("request_type", "mentor_admin_query")\
                            .order("created_at", desc=True)\
                            .execute()
                        rows = []
                        for r in (res.data or []):
                            p = r.get("profiles") or {}
                            r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                            r["aspirant_email"] = p.get("email") or ""
                            rows.append(r)
                        return _enrich_mentor_names(rows, admin_client)
                    except Exception as e2:
                        print(f"[HelpRequests] Admin fallback error: {e2}")
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

    # PART 7 — AUTHORIZATION: Verify caller is authorized
    try:
        import streamlit as st
        session_user = st.session_state.get("user")
        session_role = st.session_state.get("role")
        session_uid = st.session_state.get("user_id")
        if session_user and session_role not in ("admin", "sme"):
            return False, "Unauthorized: Only assigned SMEs or Admins may respond to this consultation."
        if session_user and session_role == "sme" and str(session_uid) != str(sme_id):
            return False, "Unauthorized: You cannot respond on behalf of another SME."
    except Exception:
        pass

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
                "sme_response": response.strip(),
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
    """
    Auto-escalation disabled.
    Under the 2-tier governance architecture, the Administrator is completely invisible to the Aspirant.
    Only Guides and Domain SMEs can escalate institutional roadblocks to the Administration on behalf of an Aspirant.
    """
    return 0

def create_mentor_admin_query(
    mentor_id: str,
    mentor_role: str,
    aspirant_id: str,
    subject: str,
    message: str,
    priority: str = "MEDIUM"
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Mentor (Guide or Domain SME) submits an institutional query / roadblock
    to the Directorate on behalf of a specific mentee (Aspirant).
    The Aspirant is never aware of this query.
    """
    if not subject or not message:
        return None, "Subject and description of roadblock are required."

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()
    req_id = str(uuid.uuid4())

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            return None, "Database client unavailable."
        req_data = {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject.strip(),
            "message": message.strip(),
            "priority": priority,
            "status": "PENDING_ADMIN",
            "requester_id": mentor_id,
            "requester_role": mentor_role,
            "request_type": "mentor_admin_query",
            "created_at": now_iso,
            "updated_at": now_iso
        }
        try:
            res = client.table("help_requests").insert(req_data).execute()
            req = res.data[0] if (res.data and len(res.data) > 0) else req_data
        except Exception as e:
            admin_client = _get_admin_client()
            inserted = False
            if admin_client and admin_client != client:
                try:
                    res = admin_client.table("help_requests").insert(req_data).execute()
                    req = res.data[0] if (res.data and len(res.data) > 0) else req_data
                    inserted = True
                except Exception:
                    pass
            if not inserted:
                print(f"[HelpRequests] Supabase insert note ({e}), saving to local fallback db")
                local_db = get_local_db()
                req = local_db.create_mentor_admin_query(
                    mentor_id=mentor_id,
                    mentor_role=mentor_role,
                    aspirant_id=aspirant_id,
                    subject=subject.strip(),
                    message=message.strip(),
                    priority=priority
                )
    else:
        local_db = get_local_db()
        req = local_db.create_mentor_admin_query(
            mentor_id=mentor_id,
            mentor_role=mentor_role,
            aspirant_id=aspirant_id,
            subject=subject.strip(),
            message=message.strip(),
            priority=priority
        )

    # Dispatch In-App Notification to Admins
    try:
        from services.notifications import create_notification
        from services.profiles import get_profile, list_profiles_by_role
        asp_p = get_profile(aspirant_id)
        asp_name = asp_p.get("full_name") if asp_p else "Entrepreneur"
        admins = list_profiles_by_role("admin")
        for adm in (admins or []):
            create_notification(
                user_id=adm["id"],
                title=f"New Mentor Inquiry ({mentor_role.upper()}): {subject.strip()}",
                message=f"A mentor requested institutional directive on behalf of {asp_name}.",
                notification_type="admin_directive_needed",
                actor_id=mentor_id
            )
    except Exception as ne:
        print(f"[HelpRequests] Admin notification warning: {ne}")

    return req, None

def list_mentor_admin_queries(
    mentor_id: Optional[str] = None,
    aspirant_id: Optional[str] = None
) -> List[Dict]:
    """
    Retrieves institutional queries submitted by mentors (Guides/SMEs) to Admin.
    Can be filtered by mentor_id, aspirant_id, or listed globally for Admin.
    """
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if client:
            try:
                q = client.table("help_requests")\
                    .select("*, profiles:aspirant_id(full_name, email), requester:requester_id(full_name, role)")\
                    .eq("request_type", "mentor_admin_query")
                if mentor_id:
                    q = q.eq("requester_id", mentor_id)
                if aspirant_id:
                    q = q.eq("aspirant_id", aspirant_id)
                res = q.order("created_at", desc=True).execute()
                rows = []
                for r in (res.data or []):
                    p = r.get("profiles") or {}
                    req_p = r.get("requester") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    r["requester_name"] = req_p.get("full_name") or "Mentor"
                    r["requester_role_actual"] = req_p.get("role") or r.get("requester_role", "guide")
                    rows.append(r)
                local_rows = get_local_db().list_mentor_admin_queries(mentor_id=mentor_id, aspirant_id=aspirant_id)
                seen_ids = {r["id"] for r in rows}
                for lr in local_rows:
                    if lr["id"] not in seen_ids:
                        rows.append(lr)
                if rows:
                    return rows
            except Exception as e:
                print(f"[HelpRequests] Supabase list_mentor_admin_queries error: {e}")

    local_rows = get_local_db().list_mentor_admin_queries(mentor_id=mentor_id, aspirant_id=aspirant_id)
    from services.profiles import get_profile
    for r in local_rows:
        if not r.get("aspirant_name") and r.get("aspirant_id"):
            p = get_profile(r["aspirant_id"])
            if p:
                r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                r["aspirant_email"] = p.get("email") or ""
        if not r.get("requester_name") and r.get("requester_id"):
            mp = get_profile(r["requester_id"])
            if mp:
                r["requester_name"] = mp.get("full_name") or "Mentor"
                r["requester_role_actual"] = mp.get("role") or r.get("requester_role", "guide")
    return local_rows

def admin_respond_to_mentor(
    query_id: str,
    admin_id: str,
    directive: str,
    new_status: str = "DIRECTIVE_ISSUED",
    assign_co_guide_id: Optional[str] = None,
    assign_sme_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Admin issues an official administrative directive to the requesting mentor (Guide or SME).
    Admin can also optionally assign Guide B (Co-Guide) or an additional Domain SME.
    The Aspirant is NEVER notified and NEVER sees the Admin.
    """
    if not directive.strip():
        return False, "Directive text is required."

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    requester_id = None
    aspirant_id = None
    subject = "Institutional Roadblock"

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            return False, "Database client unavailable."
        try:
            t_res = client.table("help_requests").select("*").eq("id", query_id).execute()
            if t_res.data and len(t_res.data) > 0:
                item = t_res.data[0]
                requester_id = item.get("requester_id")
                aspirant_id = item.get("aspirant_id")
                subject = item.get("subject") or subject

            update_payload = {
                "status": new_status,
                "admin_directive": directive.strip(),
                "directive_issued_at": now_iso,
                "responded_by": admin_id,
                "resolved_by": admin_id if new_status in ("DIRECTIVE_ISSUED", "RESOLVED") else None,
                "updated_at": now_iso
            }
            client.table("help_requests").update(update_payload).eq("id", query_id).execute()
        except Exception as e:
            print(f"[HelpRequests] Supabase admin_respond_to_mentor error: {e}")
        
        # Always synchronize directive to local_db as well
        get_local_db().admin_respond_to_mentor_query(query_id, admin_id, directive.strip(), new_status)
    else:
        local_db = get_local_db()
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT requester_id, aspirant_id, subject FROM help_requests WHERE id = ?", (query_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            requester_id = row["requester_id"]
            aspirant_id = row["aspirant_id"]
            subject = row["subject"]
        local_db.admin_respond_to_mentor_query(query_id, admin_id, directive.strip(), new_status)

    if not requester_id or not aspirant_id:
        conn = get_local_db()._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT requester_id, aspirant_id, subject FROM help_requests WHERE id = ?", (query_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            requester_id = requester_id or row["requester_id"]
            aspirant_id = aspirant_id or row["aspirant_id"]
            subject = row["subject"] or subject

    # Assign Co-Guide (Guide B) if specified
    if assign_co_guide_id and aspirant_id:
        try:
            from services.relationships import assign_guide
            assign_guide(aspirant_id, assign_co_guide_id, admin_id, notes=f"Co-Guide assigned via Admin Directive: {directive.strip()[:60]}", mode="add")
        except Exception as ge:
            print(f"[HelpRequests] Co-Guide assignment warning: {ge}")

    # Assign Domain SME if specified
    if assign_sme_id and aspirant_id:
        try:
            from services.relationships import assign_sme
            assign_sme(aspirant_id, assign_sme_id, admin_id, notes=f"Domain specialist assigned via Admin Directive: {directive.strip()[:60]}", mode="add")
        except Exception as se:
            print(f"[HelpRequests] SME assignment warning: {se}")

    # Dispatch notification ONLY to the requesting mentor (NOT the Aspirant)
    if requester_id:
        try:
            from services.notifications import create_notification
            create_notification(
                user_id=requester_id,
                title=f"Administrative Directive Issued: {subject}",
                message=f"Directorate recorded official directive: '{directive.strip()[:100]}...'",
                notification_type="admin_directive_issued",
                actor_id=admin_id
            )
        except Exception as ne:
            print(f"[HelpRequests] Mentor notification warning: {ne}")

    return True, None


def create_mentor_consultation(
    mentor_id: str,
    mentor_role: str,
    aspirant_id: str,
    subject: str,
    message: str,
    priority: str = "MEDIUM",
    category: str = "GENERAL",
    category_detail: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Mentor (Guide or Domain SME) issues a proactive guidance directive, check-in,
    or action item directly to an assigned mentee (Aspirant).
    """
    if not subject or not message:
        return None, "Subject and guidance instructions are required."

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()
    req_id = str(uuid.uuid4())
    actual_guide_id = mentor_id if mentor_role == "guide" else None
    actual_sme_id = mentor_id if mentor_role == "sme" else None
    clean_cat_detail = category_detail.strip() if category_detail else None

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            return None, "Database client unavailable."
        req_data = {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject.strip(),
            "message": message.strip(),
            "priority": priority,
            "status": "OPEN",
            "assigned_guide_id": actual_guide_id,
            "assigned_sme_id": actual_sme_id,
            "category": category,
            "category_detail": clean_cat_detail,
            "target_role": mentor_role,
            "requester_id": mentor_id,
            "requester_role": mentor_role,
            "request_type": "mentor_initiated",
            "assigned_at": now_iso,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        try:
            res = client.table("help_requests").insert(req_data).execute()
            req = res.data[0] if (res.data and len(res.data) > 0) else req_data
        except Exception as e:
            admin_client = _get_admin_client()
            inserted = False
            if admin_client and admin_client != client:
                try:
                    res = admin_client.table("help_requests").insert(req_data).execute()
                    req = res.data[0] if (res.data and len(res.data) > 0) else req_data
                    inserted = True
                except Exception:
                    pass
            if not inserted:
                print(f"[HelpRequests] Supabase insert note ({e}), saving to local fallback db")
                local_db = get_local_db()
                req = local_db.create_mentor_consultation(
                    mentor_id=mentor_id,
                    mentor_role=mentor_role,
                    aspirant_id=aspirant_id,
                    subject=subject.strip(),
                    message=message.strip(),
                    priority=priority,
                    category=category,
                    category_detail=clean_cat_detail
                )
    else:
        local_db = get_local_db()
        req = local_db.create_mentor_consultation(
            mentor_id=mentor_id,
            mentor_role=mentor_role,
            aspirant_id=aspirant_id,
            subject=subject.strip(),
            message=message.strip(),
            priority=priority,
            category=category,
            category_detail=clean_cat_detail
        )

    # Dispatch In-App Notification to the Aspirant
    try:
        from services.notifications import create_notification
        from services.profiles import get_profile
        mentor_p = get_profile(mentor_id)
        mentor_name = mentor_p.get("full_name") if mentor_p else ("Dedicated Guide" if mentor_role == "guide" else "Domain SME")
        role_label = "Dedicated Guide" if mentor_role == "guide" else "Domain Specialist"
        create_notification(
            user_id=aspirant_id,
            title=f"Guidance Directive: {subject.strip()}",
            message=f"{mentor_name} ({role_label}) issued a guidance check-in: '{message.strip()[:90]}...'",
            notification_type="mentor_guidance_issued",
            actor_id=mentor_id
        )
    except Exception as e:
        print(f"[HelpRequests] Notification dispatch error: {e}")

    return req, None


def aspirant_respond_request(request_id: str, aspirant_id: str, response: str) -> Tuple[bool, Optional[str]]:
    """
    Aspirant responds to a consultation request (especially mentor-initiated directives).
    Updates status to 'REPLIED' and records the response.
    """
    if not response or not response.strip():
        return False, "Response text is required."

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()
    mentor_recipient_id = None
    subject = "Consultation"

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            return False, "Database client unavailable."
        try:
            # Fetch request
            t_res = client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                admin_client = _get_admin_client()
                if admin_client:
                    t_res = admin_client.table("help_requests").select("*").eq("id", request_id).execute()
            if not t_res.data or len(t_res.data) == 0:
                return False, "Consultation record not found."

            req = t_res.data[0]
            if str(req.get("aspirant_id")) != str(aspirant_id):
                return False, "Unauthorized: You can only respond to your own consultations."

            subject = req.get("subject", "Consultation")
            mentor_recipient_id = req.get("requester_id") or req.get("assigned_guide_id") or req.get("assigned_sme_id")

            # Try updating with aspirant_response column, fallback to admin_response if column does not exist
            update_payload = {
                "status": "IN_PROGRESS",
                "aspirant_response": response.strip(),
                "last_handled_at": now_iso,
                "updated_at": now_iso
            }
            try:
                client.table("help_requests").update(update_payload).eq("id", request_id).execute()
            except Exception:
                update_payload.pop("aspirant_response", None)
                update_payload["admin_response"] = f"Aspirant Reply: {response.strip()}"
                client.table("help_requests").update(update_payload).eq("id", request_id).execute()

        except Exception as e:
            admin_client = _get_admin_client()
            if admin_client and admin_client != client:
                try:
                    fallback_payload = {
                        "status": "IN_PROGRESS",
                        "admin_response": f"Aspirant Reply: {response.strip()}",
                        "last_handled_at": now_iso,
                        "updated_at": now_iso
                    }
                    admin_client.table("help_requests").update(fallback_payload).eq("id", request_id).execute()
                except Exception as e2:
                    return False, f"Failed to submit response to Supabase: {e2}"
            else:
                return False, f"Failed to submit response to Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False, "Consultation record not found."
        req = dict(row)
        if str(req.get("aspirant_id")) != str(aspirant_id):
            return False, "Unauthorized: You can only respond to your own consultations."

        subject = req.get("subject", "Consultation")
        mentor_recipient_id = req.get("requester_id") or req.get("assigned_guide_id") or req.get("assigned_sme_id")
        local_db.aspirant_respond_help_request(request_id, aspirant_id, response.strip())

    # Dispatch notification to mentor
    if mentor_recipient_id:
        try:
            from services.notifications import create_notification
            from services.profiles import get_profile
            asp_p = get_profile(aspirant_id)
            asp_name = asp_p.get("full_name") if asp_p else "Entrepreneur"
            create_notification(
                user_id=mentor_recipient_id,
                title=f"Reply from {asp_name}: {subject}",
                message=f"{asp_name} replied to your consultation inquiry: '{response.strip()[:90]}...'",
                notification_type="aspirant_reply_submitted",
                actor_id=aspirant_id
            )
        except Exception as e:
            print(f"[HelpRequests] Notification dispatch error: {e}")

    return True, None

