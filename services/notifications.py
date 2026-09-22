"""
services/notifications.py — Universal In-App Notification System for FULCRUM-INDIA
==================================================================================
Real-time notification engine for all roles (Aspirant, Guide, SME, Admin):
- Mentor assignments and handoffs
- Scheme recommendations and releases
- Support tickets and expert replies
- Administrative alerts and milestones

Production Rule (PART 2 & PART 8):
- When DATA_BACKEND=supabase: strictly Supabase ONLY. Zero silent fallback to SQLite.
- Authorization: Enforces strict relationship checks. Unauthorized cross-user notifications are blocked.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client, get_supabase_admin_client, get_data_backend
from services.logger import app_logger

def _get_user_client():
    return get_supabase_client()

def _get_admin_client():
    return get_supabase_admin_client()

def is_notification_allowed(actor_id: Optional[str], target_user_id: str, notification_type: str) -> bool:
    """
    PART 8 — NOTIFICATION SAFETY
    Verifies that actor_id is authorized to notify target_user_id.
    - System/automated (actor_id None): Allowed.
    - Self notification: Allowed.
    - Admin actor: Allowed to notify anyone.
    - Target is Admin: Any authenticated user can notify Admin.
    - Aspirant actor: Can only notify assigned Guide(s) or SME(s).
    - Guide actor: Can only notify an assigned Aspirant.
    - SME actor: Can only notify an assigned Aspirant.
    - All other arbitrary cross-user notifications are blocked.
    """
    if not actor_id or actor_id == target_user_id:
        return True

    from services.profiles import get_profile
    from services.relationships import get_aspirant_mentors

    actor_prof = get_profile(actor_id)
    if not actor_prof:
        return False
    actor_role = actor_prof.get("role", "aspirant")

    if actor_role == "admin":
        return True

    target_prof = get_profile(target_user_id)
    if not target_prof:
        return False
    target_role = target_prof.get("role", "aspirant")

    # Anyone can notify an Admin (support/escalation)
    if target_role == "admin":
        return True

    if actor_role == "aspirant":
        mentors = get_aspirant_mentors(actor_id) or {}
        valid_mentor_ids = [m["id"] for m in mentors.get("guides", [])] + [m["id"] for m in mentors.get("smes", [])]
        return target_user_id in valid_mentor_ids

    if actor_role in ("guide", "sme"):
        mentors = get_aspirant_mentors(target_user_id) or {}
        if actor_role == "guide":
            valid_guide_ids = [m["id"] for m in mentors.get("guides", [])]
            return actor_id in valid_guide_ids
        elif actor_role == "sme":
            valid_sme_ids = [m["id"] for m in mentors.get("smes", [])]
            return actor_id in valid_sme_ids

    return False

def create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    actor_id: Optional[str] = None,
    link: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Creates an in-app notification for a specific user.
    Types: 'guide_assigned', 'guide_reassigned', 'sme_assigned', 'sme_reassigned',
           'scheme_released', 'help_ticket_created', 'help_ticket_replied', 'system_alert'
    """
    if not user_id or not title:
        return None, "user_id and title are required."

    # PART 8: Relationship & Authorization Validation
    if not is_notification_allowed(actor_id, user_id, notification_type):
        err = f"Unauthorized: User {actor_id} is not permitted to send notifications to {user_id}."
        app_logger.warning("notifications", "create_notification_blocked", err, actor_id=actor_id)
        return None, "Unauthorized: Notification recipient is not in an authorized relationship with the sender."

    backend = get_data_backend()
    notif_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    notif_data = {
        "id": notif_id,
        "user_id": user_id,
        "actor_id": actor_id,
        "title": title.strip(),
        "message": message.strip() if message else "",
        "notification_type": notification_type,
        "link": link,
        "is_read": False,
        "created_at": now_iso
    }

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            app_logger.error("notifications", "create_notification", "Supabase client unavailable", actor_id=actor_id)
            return None, "Supabase client unavailable."
        try:
            res = client.table("notifications").insert(notif_data).execute()
            if res.data and len(res.data) > 0:
                app_logger.info("notifications", "create_notification", f"Notification created for {user_id}", actor_id=actor_id)
                return res.data[0], None
            return notif_data, None
        except Exception as e:
            app_logger.error("notifications", "create_notification", f"Supabase notification insert failed: {e}", error=e, actor_id=actor_id)
            return None, f"Failed to record notification in Supabase: {e}"

    # SQLite local mode (ONLY when DATA_BACKEND=sqlite)
    from services.local_db import get_local_db
    try:
        rec = get_local_db().create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            actor_id=actor_id,
            link=link
        )
        return rec, None
    except Exception as e:
        return None, f"Local DB notification error: {e}"

def list_notifications(user_id: str, unread_only: bool = False) -> List[Dict]:
    """Retrieves notifications for a user."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                q = client.table("notifications").select("*").eq("user_id", user_id)
                if unread_only:
                    q = q.eq("is_read", False)
                res = q.order("created_at", desc=True).limit(50).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                app_logger.error("notifications", "list_notifications", f"Supabase list error for {user_id}: {e}", error=e, actor_id=user_id)
                admin = _get_admin_client()
                if admin and admin != client:
                    try:
                        q2 = admin.table("notifications").select("*").eq("user_id", user_id)
                        if unread_only:
                            q2 = q2.eq("is_read", False)
                        res2 = q2.order("created_at", desc=True).limit(50).execute()
                        if res2.data is not None:
                            return res2.data
                    except Exception:
                        pass
        return []

    # SQLite local mode ONLY
    from services.local_db import get_local_db
    try:
        return get_local_db().list_notifications(user_id=user_id, unread_only=unread_only)
    except Exception as e:
        print(f"[Notifications] Local DB query error: {e}")
        return []

def mark_as_read(notification_id: str, user_id: str) -> bool:
    """Marks a specific notification as read."""
    backend = get_data_backend()

    if backend == "supabase":
        user_client = _get_user_client()
        admin = _get_admin_client()
        if user_client:
            try:
                res = user_client.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
                if res.data:
                    return True
            except Exception:
                pass
        if admin:
            try:
                res = admin.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
                return bool(res.data)
            except Exception as e:
                app_logger.error("notifications", "mark_as_read", f"Supabase mark_as_read error: {e}", error=e, actor_id=user_id)
                return False
        return False

    from services.local_db import get_local_db
    try:
        return get_local_db().mark_notification_as_read(notification_id, user_id)
    except Exception:
        return False

def mark_all_as_read(user_id: str) -> bool:
    """Marks all unread notifications for a user as read."""
    backend = get_data_backend()

    if backend == "supabase":
        user_client = _get_user_client()
        admin = _get_admin_client()
        if user_client:
            try:
                res = user_client.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
                if res.data is not None:
                    return True
            except Exception:
                pass
        if admin:
            try:
                res = admin.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
                return res.data is not None
            except Exception as e:
                app_logger.error("notifications", "mark_all_as_read", f"Supabase mark_all_as_read error: {e}", error=e, actor_id=user_id)
                return False
        return False

    from services.local_db import get_local_db
    try:
        return get_local_db().mark_all_notifications_as_read(user_id)
    except Exception:
        return False

def get_unread_count(user_id: str) -> int:
    """Returns the count of unread notifications for a user."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                res = client.table("notifications").select("id", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
                if hasattr(res, "count") and res.count is not None:
                    return int(res.count)
                if res.data is not None:
                    return len(res.data)
            except Exception as e:
                app_logger.error("notifications", "get_unread_count", f"Supabase unread count error: {e}", error=e, actor_id=user_id)
                return 0
        return 0

    from services.local_db import get_local_db
    try:
        return get_local_db().get_unread_notifications_count(user_id)
    except Exception:
        return 0
