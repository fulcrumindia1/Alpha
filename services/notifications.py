"""
services/notifications.py — Universal In-App Notification System for FULCRUM-INDIA
==================================================================================
Real-time notification engine for all roles (Aspirant, Guide, SME, Admin):
- Mentor assignments and handoffs
- Scheme recommendations and releases
- Support tickets and expert replies
- Administrative alerts and milestones
Supports dual backends: Supabase (primary cloud) and SQLite (resilient local/dev).
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client, get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

def _get_user_client():
    return get_supabase_client()

def _get_admin_client():
    return get_supabase_admin_client()

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
            return None, "Supabase client unavailable."
        try:
            res = client.table("notifications").insert(notif_data).execute()
            if res.data and len(res.data) > 0:
                return res.data[0], None
            return notif_data, None
        except Exception as e:
            # Fallback to local db if Supabase insert fails
            print(f"[Notifications] Supabase insert error: {e}")
            try:
                local_rec = get_local_db().create_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    actor_id=actor_id,
                    link=link
                )
                return local_rec, None
            except Exception:
                return notif_data, None
    else:
        # SQLite local mode
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
                print(f"[Notifications] Supabase list error: {e}")
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

    # SQLite fallback
    try:
        return get_local_db().list_notifications(user_id=user_id, unread_only=unread_only)
    except Exception as e:
        print(f"[Notifications] Local DB query error: {e}")
        return []

def mark_as_read(notification_id: str, user_id: str) -> bool:
    """Marks a specific notification as read."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                res = client.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
                if res.data:
                    return True
            except Exception as e:
                print(f"[Notifications] Supabase mark_as_read error: {e}")

    try:
        return get_local_db().mark_notification_as_read(notification_id, user_id)
    except Exception:
        return False

def mark_all_as_read(user_id: str) -> bool:
    """Marks all unread notifications for a user as read."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if client:
            try:
                res = client.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
                if res.data is not None:
                    return True
            except Exception as e:
                print(f"[Notifications] Supabase mark_all_as_read error: {e}")

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
            except Exception:
                pass

    try:
        return get_local_db().get_unread_notifications_count(user_id)
    except Exception:
        return 0
