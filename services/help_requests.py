"""
services/help_requests.py — Support & Communication Service for FULCRUM-INDIA
=============================================================================
Replaces complex WebSockets/chat with a lean, reliable ticketing queue.
- Aspirants raise help requests with subject, message, priority.
- Admin updates status (OPEN, IN_PROGRESS, RESOLVED) and responds.
- Automatically logs meaningful Journey events upon creation and resolution.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client
from services.local_db import get_local_db

def create_request(aspirant_id: str, subject: str, message: str, priority: str = "MEDIUM") -> Tuple[Optional[Dict], Optional[str]]:
    """Aspirant submits a support/help request."""
    if not subject or not message:
        return None, "Subject and message are required."

    local_db = get_local_db()
    req = local_db.create_help_request(aspirant_id, subject.strip(), message.strip(), priority)

    # Supabase sync
    client = get_supabase_client()
    if client:
        try:
            client.table("help_requests").insert({
                "id": req["id"],
                "aspirant_id": aspirant_id,
                "subject": subject.strip(),
                "message": message.strip(),
                "priority": priority,
                "status": "OPEN"
            }).execute()
        except Exception:
            pass

    # Log Journey event
    from services.journey import log_meaningful_event
    log_meaningful_event(
        aspirant_id=aspirant_id,
        actor_id=aspirant_id,
        actor_role="aspirant",
        event_type="help_requested",
        title="Support Requested",
        description=f"Raised help ticket: '{subject.strip()}' (Priority: {priority}).",
        metadata={"ticket_id": req["id"], "priority": priority}
    )

    return req, None

def list_requests(aspirant_id: Optional[str] = None) -> List[Dict]:
    """Retrieves tickets for an Aspirant or all tickets for Admin."""
    client = get_supabase_client()
    if client:
        try:
            q = client.table("help_requests").select("*, profiles:aspirant_id(full_name, email)")
            if aspirant_id:
                q = q.eq("aspirant_id", aspirant_id)
            res = q.order("created_at", desc=True).execute()
            if res.data:
                rows = []
                for r in res.data:
                    p = r.get("profiles") or {}
                    r["aspirant_name"] = p.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = p.get("email") or ""
                    rows.append(r)
                return rows
        except Exception:
            pass

    return get_local_db().list_help_requests(aspirant_id)

def resolve_request(request_id: str, new_status: str, admin_response: str, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Admin updates ticket status and records official response."""
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

    # Supabase sync
    client = get_supabase_client()
    if client:
        try:
            client.table("help_requests").update({
                "status": new_status,
                "admin_response": admin_response.strip(),
                "responded_by": admin_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", request_id).execute()
        except Exception:
            pass

    local_db.update_help_request_status(request_id, new_status, admin_response.strip(), admin_id)

    # Log Journey event if resolved
    if new_status == "RESOLVED":
        from services.journey import log_meaningful_event
        log_meaningful_event(
            aspirant_id=aspirant_id,
            actor_id=admin_id,
            actor_role="admin",
            event_type="help_resolved",
            title="Help Request Resolved",
            description=f"Admin resolved '{subject}'. Response: {admin_response.strip()}",
            metadata={"ticket_id": request_id}
        )

    return True, None
