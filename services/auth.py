"""
services/auth.py — Authentication & RBAC Service for FULCRUM-INDIA
===================================================================
Manages Supabase Auth, session tokens, and database-driven user roles.
Supports dual backend architecture:
- Primary: Supabase Auth & PostgreSQL with RLS (Production & Cloud Dev)
- Fallback: SQLite cluster_a.db (Explicit Local Dev & Offline Testing Only)
No hardcoded secrets. Deterministic backend selection via DATA_BACKEND.
"""

import os
import streamlit as st
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

# Local fallback SQLite store for explicit offline development
from services.local_db import get_local_db

def _get_secrets() -> Tuple[str, str, str]:
    """
    Retrieves Supabase URL, Publishable/Anon Key, and Secret/Service-Role Key.
    Checks st.secrets first, then os.environ.
    Supports both modern Supabase names:
      - SUPABASE_PUBLISHABLE_KEY
      - SUPABASE_SECRET_KEY
    and standard names:
      - SUPABASE_ANON_KEY
      - SUPABASE_SERVICE_ROLE_KEY
    Never contains hardcoded credentials.
    """
    url = ""
    pub_key = ""
    sec_key = ""

    # 1. Streamlit secrets
    try:
        if hasattr(st, "secrets"):
            url = st.secrets.get("SUPABASE_URL", "")
            pub_key = st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
            sec_key = st.secrets.get("SUPABASE_SECRET_KEY", "") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except Exception:
        pass

    # 2. Environment variables fallback
    if not url:
        url = os.environ.get("SUPABASE_URL", "")
    if not pub_key:
        pub_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not sec_key:
        sec_key = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    return url.strip(), pub_key.strip(), sec_key.strip()

def get_data_backend() -> str:
    """
    Determines the active backend: 'supabase' or 'sqlite'.
    Explicitly reads DATA_BACKEND from Streamlit secrets or environment variables.
    Defaults to 'supabase' if Supabase credentials are configured, else 'sqlite'.
    """
    backend = os.environ.get("DATA_BACKEND", "")
    if not backend:
        try:
            if hasattr(st, "secrets"):
                backend = st.secrets.get("DATA_BACKEND", "")
        except Exception:
            pass

    backend = backend.strip().lower()
    if backend in ("supabase", "sqlite"):
        return backend

    url, pub_key, _ = _get_secrets()
    if url and pub_key:
        return "supabase"
    return "sqlite"

def is_supabase_enabled() -> bool:
    """Returns True if DATA_BACKEND is configured for Supabase and credentials exist."""
    if get_data_backend() != "supabase":
        return False
    url, pub_key, _ = _get_secrets()
    return bool(url and pub_key and create_client)

def get_supabase_client() -> Optional[Client]:
    """Returns a per-session Supabase public client with auth state."""
    url, pub_key, _ = _get_secrets()
    if not url or not pub_key or not create_client:
        return None

    try:
        if "supabase_client" not in st.session_state or st.session_state.supabase_client is None:
            st.session_state.supabase_client = create_client(url, pub_key)

        client = st.session_state.supabase_client

        # Synchronize active tokens if present in session state
        token = st.session_state.get("sb_access_token")
        refresh_token = st.session_state.get("sb_refresh_token")
        if client and token and refresh_token:
            try:
                curr = client.auth.get_session()
                if not curr or curr.access_token != token:
                    client.auth.set_session(token, refresh_token)
            except Exception:
                pass

        return client
    except Exception:
        try:
            return create_client(url, pub_key)
        except Exception:
            return None

@st.cache_resource
def get_supabase_admin_client() -> Optional[Client]:
    """Returns trusted server-side Supabase client with secret/service_role privileges.
    Cached as a process-level singleton — the service-role client is stateless."""
    url, _, sec_key = _get_secrets()
    if not url or not sec_key or not create_client:
        return None
    try:
        return create_client(url, sec_key)
    except Exception:
        return None

def sync_user_phone_if_missing(user_id: str, phone: str, district: Optional[str] = None) -> bool:
    """Self-healing utility: updates missing phone/district in profiles table and profile_data."""
    if not user_id or not phone:
        return False
    backend = get_data_backend()
    if backend == "supabase":
        client = get_supabase_admin_client() or get_supabase_client()
        if client:
            try:
                upd = {"phone": phone}
                if district:
                    upd["district"] = district
                client.table("profiles").update(upd).eq("id", user_id).execute()
                return True
            except Exception:
                pass
    try:
        from services.local_db import get_local_db
        db = get_local_db()
        p = db.get_profile_by_id(user_id)
        if p:
            p_data = p.get("profile_data") or {}
            if isinstance(p_data, str):
                import json
                try:
                    p_data = json.loads(p_data)
                except Exception:
                    p_data = {}
            p_pers = p_data.setdefault("personal", {})
            p_pers["phone"] = phone
            if district:
                p_pers["district"] = district
            p["phone"] = phone
            if district:
                p["district"] = district
            p["profile_data"] = p_data
            db.upsert_profile(p)
            return True
    except Exception as e:
        print(f"[Auth] sync_user_phone error: {e}")
    return False

def login_user(email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Authenticates user.
    When DATA_BACKEND=supabase: strictly uses Supabase Auth; respects email confirmation.
    When DATA_BACKEND=sqlite: authenticates against local SQLite.
    Returns (user_profile_dict, error_message).
    """
    email = email.strip().lower()
    password = password.strip()
    if not email or not password:
        return None, "Please provide both email and password."

    backend = get_data_backend()

    # ── SQLITE LOCAL MODE ──
    if backend == "sqlite":
        local_db = get_local_db()
        local_profile = local_db.get_profile_by_email(email)
        if local_profile and local_db.verify_password(email, password):
            st.session_state.user = local_profile
            st.session_state.user_id = local_profile["id"]
            st.session_state.role = local_profile.get("role", "aspirant")
            return local_profile, None
        return None, "Invalid email or password (Local SQLite Mode)."

    # ── SUPABASE PRIMARY MODE ──
    client = get_supabase_client()
    if not client:
        return None, "Supabase connection is not configured. Please check SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."

    user_id = None
    access_token = None
    refresh_token = None

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            user_id = res.user.id
            if res.session:
                access_token = res.session.access_token
                refresh_token = res.session.refresh_token
    except Exception as e:
        err_str = str(e)
        if "email not confirmed" in err_str.lower() or "unconfirmed" in err_str.lower():
            return None, "Your email address has not been confirmed yet. Please check your inbox for the confirmation email."
        if "invalid login credentials" in err_str.lower() or "invalid_grant" in err_str.lower():
            return None, "Invalid email or password."
        return None, f"Authentication error: {err_str}"

    if not user_id:
        return None, "Invalid email or password."

    # Retrieve profile from Supabase Database
    profile = None
    try:
        res_p = client.table("profiles").select("*").eq("id", user_id).execute()
        if res_p.data and len(res_p.data) > 0:
            profile = res_p.data[0]
    except Exception as e:
        return None, f"Database profile error: {e}"

    # Auto-backfill profile if user exists in Supabase Auth but lacks a profiles row
    if not profile and user_id:
        admin_client = get_supabase_admin_client() or client
        try:
            # Look up metadata from Auth user
            user_meta = {}
            if res.user and hasattr(res.user, "user_metadata"):
                user_meta = res.user.user_metadata or {}

            full_name = user_meta.get("full_name") or email.split("@")[0].capitalize()
            role = user_meta.get("role", "aspirant")
            district = user_meta.get("district", "Tamil Nadu")

            new_profile = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "phone": user_meta.get("phone", ""),
                "role": role,
                "district": district,
                "state": "Tamil Nadu",
                "profile_data": {
                    "personal": {"full_name": full_name, "email": email, "phone": user_meta.get("phone", ""), "district": district}
                },
                "is_active": True
            }
            admin_client.table("profiles").upsert(new_profile, on_conflict="id").execute()
            profile = new_profile

            if role == "aspirant":
                admin_client.table("journeys").upsert({
                    "aspirant_id": user_id,
                    "title": f"{full_name}'s Enterprise Journey",
                    "business_type": "Entrepreneurship",
                    "stage": "idea",
                    "status": "active"
                }, on_conflict="aspirant_id").execute()

                admin_client.table("relationships").upsert({
                    "aspirant_id": user_id,
                    "status": "active"
                }, on_conflict="aspirant_id").execute()
        except Exception as e:
            return None, f"Failed to initialize user profile: {e}"

    if not profile:
        return None, "User profile not found in Supabase database."

    # Self-heal phone number if missing in profile record but present in user metadata
    if profile and res.user:
        user_meta = getattr(res.user, "user_metadata", {}) or {}
        meta_phone = user_meta.get("phone")
        if meta_phone and not profile.get("phone"):
            profile["phone"] = meta_phone
            sync_user_phone_if_missing(user_id, meta_phone, user_meta.get("district"))

    # Save authenticated session state
    st.session_state.user = profile
    st.session_state.user_id = profile["id"]
    st.session_state.role = profile.get("role", "aspirant")
    if access_token:
        st.session_state.sb_access_token = access_token
        st.session_state.sb_refresh_token = refresh_token

    return profile, None

def signup_aspirant(email: str, password: str, full_name: str, phone: str = "", district: str = "Madurai") -> Tuple[Optional[Dict], Optional[str]]:
    """
    Public Aspirant Signup. Strictly sets role = 'aspirant'.
    When DATA_BACKEND=supabase: uses Supabase Auth with email confirmation redirect.
    When DATA_BACKEND=sqlite: creates local SQLite account.
    """
    email = email.strip().lower()
    full_name = full_name.strip()
    if not email or not password or not full_name:
        return None, "Please fill in all required fields."

    if len(password) < 6:
        return None, "Password must be at least 6 characters long."

    backend = get_data_backend()

    # ── SQLITE LOCAL MODE ──
    if backend == "sqlite":
        local_db = get_local_db()
        existing = local_db.get_profile_by_email(email)
        if existing:
            return None, "An account with this email already exists in local database."

        import uuid
        user_id = str(uuid.uuid4())
        profile = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "role": "aspirant",
            "district": district,
            "state": "Tamil Nadu",
            "profile_data": {
                "personal": {"full_name": full_name, "email": email, "phone": phone, "district": district},
                "business": {"business_name": f"{full_name}'s Enterprise", "stage": "idea"},
                "demographics": {"district": district, "state": "Tamil Nadu"}
            },
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        local_db.create_user_with_password(email, password, profile)
        local_db.create_initial_journey(user_id, f"{full_name}'s Enterprise Journey")

        st.session_state.user = profile
        st.session_state.user_id = profile["id"]
        st.session_state.role = "aspirant"
        return profile, None

    # ── SUPABASE PRIMARY MODE ──
    client = get_supabase_client()
    if not client:
        return None, "Supabase client is not available. Please verify credentials."

    try:
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "role": "aspirant",
                    "district": district,
                    "phone": phone
                },
                "email_redirect_to": "https://fulcrum-india.streamlit.app"
            }
        })
    except Exception as e:
        err_str = str(e)
        if "already registered" in err_str.lower() or "user already exists" in err_str.lower():
            return None, "An account with this email already exists. Please sign in."
        return None, f"Signup failed: {err_str}"

    if not res.user:
        return None, "Failed to register account with Supabase Auth."

    user_id = res.user.id

    # If email confirmation is required, res.session is None
    if not res.session:
        # Pre-seed profile with phone so race condition doesn't drop it
        admin_client = get_supabase_admin_client()
        if admin_client:
            try:
                admin_client.table("profiles").upsert({
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "phone": phone,
                    "role": "aspirant",
                    "district": district,
                    "state": "Tamil Nadu",
                    "profile_data": {
                        "personal": {"full_name": full_name, "email": email, "phone": phone, "district": district},
                        "business": {"business_name": f"{full_name}'s Enterprise", "stage": "idea"},
                        "demographics": {"district": district, "state": "Tamil Nadu"}
                    },
                    "is_active": True
                }, on_conflict="id").execute()
            except Exception:
                pass
        return {
            "id": user_id,
            "email": email,
            "pending_confirmation": True
        }, None

    # If email confirmation is disabled or user auto-confirmed:
    profile = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "role": "aspirant",
        "district": district,
        "state": "Tamil Nadu",
        "profile_data": {
            "personal": {"full_name": full_name, "email": email, "phone": phone, "district": district},
            "business": {"business_name": f"{full_name}'s Enterprise", "stage": "idea"},
            "demographics": {"district": district, "state": "Tamil Nadu"}
        },
        "is_active": True
    }

    try:
        client.table("profiles").upsert(profile, on_conflict="id").execute()
        client.table("journeys").upsert({
            "aspirant_id": user_id,
            "title": f"{full_name}'s Enterprise Journey",
            "business_type": "Entrepreneurship",
            "stage": "idea",
            "status": "active"
        }, on_conflict="aspirant_id").execute()
        client.table("relationships").upsert({
            "aspirant_id": user_id,
            "status": "active"
        }, on_conflict="aspirant_id").execute()
    except Exception:
        pass

    st.session_state.user = profile
    st.session_state.user_id = profile["id"]
    st.session_state.role = "aspirant"
    if res.session:
        st.session_state.sb_access_token = res.session.access_token
        st.session_state.sb_refresh_token = res.session.refresh_token

    return profile, None

def send_password_reset(email: str) -> Tuple[bool, Optional[str]]:
    """
    Triggers a password recovery email via Supabase Auth.
    Directs the user back to the application URL: https://fulcrum-india.streamlit.app
    """
    email = email.strip().lower()
    if not email:
        return False, "Please enter your registered email address."

    if get_data_backend() == "sqlite":
        return False, "Password reset via email is only supported in Supabase mode."

    client = get_supabase_client()
    if not client:
        return False, "Supabase connection unavailable."

    try:
        client.auth.reset_password_for_email(
            email,
            {"redirect_to": "https://fulcrum-india.streamlit.app/?type=recovery"}
        )
        return True, None
    except Exception as e:
        return False, f"Password reset request failed: {e}"

def complete_password_reset(
    new_password: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    email: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Updates user password following recovery redirect or direct email password update.
    Supports:
    1. Supabase Auth token session update (if token available).
    2. Direct Supabase Admin API password update by registered email.
    3. SQLite local DB mirror update.
    """
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters long."

    clean_email = (email or "").strip().lower()
    backend = get_data_backend()

    if backend == "sqlite":
        if not clean_email:
            return False, "Please enter your registered email address."
        from services.local_db import get_local_db_conn
        import hashlib
        pwd_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
        try:
            conn = get_local_db_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM profiles WHERE LOWER(email) = ?", (clean_email,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return False, f"No registered account found with email: {clean_email}"
            cur.execute("UPDATE profiles SET password_hash = ? WHERE LOWER(email) = ?", (pwd_hash, clean_email))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, f"Failed to update local password: {e}"

    # Supabase mode
    client = get_supabase_client()
    admin_client = get_supabase_admin_client()

    token = access_token or st.session_state.get("sb_access_token")
    ref_token = refresh_token or st.session_state.get("sb_refresh_token") or token

    updated = False

    # 1. Attempt token-based session update if token is present
    if client and token:
        try:
            client.auth.set_session(token, ref_token or token)
            res = client.auth.update_user({"password": new_password})
            if res and getattr(res, "user", None):
                updated = True
        except Exception as e:
            print(f"[Auth] Token-based update attempt notice: {e}")

    # 2. Attempt Admin Client update by resolving registered email to user ID
    if not updated and admin_client and clean_email:
        try:
            prof_res = admin_client.table("profiles").select("id").ilike("email", clean_email).execute()
            user_id = None
            if prof_res.data and len(prof_res.data) > 0:
                user_id = prof_res.data[0].get("id")

            if not user_id:
                try:
                    users_list = admin_client.auth.admin.list_users()
                    for u in users_list:
                        if getattr(u, "email", "").lower() == clean_email:
                            user_id = getattr(u, "id", None)
                            break
                except Exception:
                    pass

            if user_id:
                admin_client.auth.admin.update_user_by_id(user_id, {"password": new_password})
                updated = True
            else:
                return False, f"No registered account found with email: {clean_email}. Please check your email address."
        except Exception as e:
            return False, f"Failed to reset password in Supabase Auth: {e}"

    if updated:
        # Also keep local SQLite DB in sync
        try:
            from services.local_db import get_local_db_conn
            import hashlib
            pwd_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
            conn = get_local_db_conn()
            cur = conn.cursor()
            cur.execute("UPDATE profiles SET password_hash = ? WHERE LOWER(email) = ?", (pwd_hash, clean_email))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return True, None

    if not clean_email and not token:
        return False, "Please enter your registered email address."

    return False, "Unable to update password. Please verify your registered email address or request a new reset link."

def complete_first_login_password_change(
    user_id: str,
    new_password: str
) -> Tuple[bool, Optional[str]]:
    """
    Enforces the first-login permanent password change for accounts provisioned with a temporary password.
    Updates the password in Supabase Auth or SQLite local DB, and sets temp_password_issued: False in profile_data.
    """
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters long."

    backend = get_data_backend()
    from services.profiles import get_profile, update_profile

    if backend == "sqlite":
        db = get_local_db()
        success = db.update_user_password(user_id, new_password)
        if not success:
            return False, "Failed to update password in local database."
        prof = get_profile(user_id)
        prof_data = (prof.get("profile_data") or {}) if prof else {}
        if isinstance(prof_data, str):
            import json
            try: prof_data = json.loads(prof_data)
            except Exception: prof_data = {}
        prof_data["temp_password_issued"] = False
        try:
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE profiles SET profile_data = ?, updated_at = ? WHERE id = ?", (
                json.dumps(prof_data),
                datetime.now(timezone.utc).isoformat(),
                user_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Auth] Local DB profile update error: {e}")

        fresh_prof = get_profile(user_id)
        if fresh_prof and "user" in st.session_state:
            st.session_state.user = fresh_prof
        elif st.session_state.get("user") and st.session_state.user.get("id") == user_id:
            st.session_state.user["profile_data"] = prof_data
        return True, None

    # Supabase mode
    admin_client = get_supabase_admin_client()
    client = get_supabase_client()
    updated = False

    if client and st.session_state.get("sb_access_token"):
        try:
            client.auth.set_session(st.session_state.sb_access_token, st.session_state.get("sb_refresh_token") or st.session_state.sb_access_token)
            client.auth.update_user({"password": new_password})
            updated = True
        except Exception as e:
            print(f"[Auth] Client password update notice: {e}")

    if not updated and admin_client:
        try:
            admin_client.auth.admin.update_user_by_id(user_id, {"password": new_password})
            updated = True
        except Exception as e:
            return False, f"Failed to update password in Supabase Auth: {e}"

    if not updated:
        return False, "Authentication client unavailable to update password."

    prof = get_profile(user_id)
    prof_data = (prof.get("profile_data") or {}) if prof else {}
    if isinstance(prof_data, str):
        import json
        try: prof_data = json.loads(prof_data)
        except Exception: prof_data = {}
    prof_data["temp_password_issued"] = False

    if admin_client:
        try:
            upd_res = admin_client.table("profiles").update({
                "profile_data": prof_data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", user_id).execute()
            if not upd_res.data and hasattr(upd_res, "error") and upd_res.error:
                return False, f"Password updated in Auth, but profile update failed: {upd_res.error}"
        except Exception as e:
            return False, f"Password updated in Auth, but failed to persist permanent status in profile: {e}"

    # Synchronize SQLite Database
    try:
        local_db = get_local_db()
        local_db.update_user_password(user_id, new_password)
        conn = local_db._get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE profiles SET profile_data = ?, updated_at = ? WHERE id = ?", (
            json.dumps(prof_data),
            datetime.now(timezone.utc).isoformat(),
            user_id
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass

    fresh_prof = get_profile(user_id)
    if fresh_prof and "user" in st.session_state:
        st.session_state.user = fresh_prof
    elif st.session_state.get("user") and st.session_state.user.get("id") == user_id:
        st.session_state.user["profile_data"] = prof_data

    return True, None

def admin_create_mentor(admin_user_id: str, role: str, full_name: str, email: str, phone: str, location: str, expertise: str, temp_password: str = "Welcome@2026", bio: str = "", industry: str = "") -> Tuple[Optional[Dict], Optional[str]]:
    """
    Administrative creation of Guide or SME accounts.
    Strictly restricted to Admin. No public signup allowed for these roles.
    """
    if role not in ("guide", "sme"):
        return None, f"Invalid mentor role: {role}"

    email = email.strip().lower()
    full_name = full_name.strip()
    if not email or not full_name:
        return None, "Name and email are required."

    backend = get_data_backend()

    if backend == "sqlite":
        local_db = get_local_db()
        import uuid
        mentor_user_id = str(uuid.uuid4())
        profile = {
            "id": mentor_user_id,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "role": role,
            "district": location,
            "state": "Tamil Nadu",
            "profile_data": {
                "expertise": expertise,
                "bio": bio,
                "industry": industry,
                "temp_password_issued": True
            },
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        local_db.create_user_with_password(email, temp_password, profile)
        local_db.log_activity(admin_user_id, f"create_{role}", "profiles", mentor_user_id, {"full_name": full_name, "email": email})
        return profile, None

    # Supabase mode
    admin_client = get_supabase_admin_client()
    if not admin_client:
        return None, "Supabase admin client (SUPABASE_SECRET_KEY) is required to create mentor accounts."

    mentor_user_id = None
    try:
        res = admin_client.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "role": role,
                "district": location,
                "phone": phone
            }
        })
        if res.user:
            mentor_user_id = res.user.id
    except Exception as e:
        err_str = str(e)
        if "already registered" in err_str.lower() or "user already exists" in err_str.lower():
            return None, "A user with this email already exists in Supabase Auth."
        return None, f"Failed to create mentor in Supabase Auth: {err_str}"

    if not mentor_user_id:
        return None, "Failed to obtain mentor user ID."

    profile = {
        "id": mentor_user_id,
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "role": role,
        "district": location,
        "state": "Tamil Nadu",
        "profile_data": {
            "expertise": expertise,
            "bio": bio,
            "industry": industry,
            "temp_password_issued": True
        },
        "is_active": True
    }

    try:
        admin_client.table("profiles").upsert(profile, on_conflict="id").execute()
    except Exception as e:
        return None, f"Failed to save mentor profile in Supabase database: {e}"

    return profile, None

def backfill_auth_users(default_admin_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely backfills missing profiles, journeys, and relationship records in Supabase
    for existing Supabase Auth users (e.g. users registered before triggers were installed).
    Idempotent: does not delete or duplicate any records.
    """
    admin_client = get_supabase_admin_client()
    if not admin_client:
        return {"error": "Supabase admin client unavailable."}

    try:
        users = admin_client.auth.admin.list_users()
    except Exception as e:
        return {"error": f"Failed to list Supabase Auth users: {e}"}

    results = {"total_auth_users": len(users), "backfilled": 0, "already_existing": 0, "errors": []}

    for u in users:
        try:
            p_res = admin_client.table("profiles").select("id, role").eq("id", u.id).execute()
            if p_res.data and len(p_res.data) > 0:
                results["already_existing"] += 1
                # Check if this user should be promoted to admin
                if default_admin_email and u.email and u.email.lower() == default_admin_email.lower():
                    admin_client.table("profiles").update({"role": "admin"}).eq("id", u.id).execute()
                continue

            # Missing profile: generate and insert
            meta = u.user_metadata or {}
            full_name = meta.get("full_name") or (u.email.split("@")[0].capitalize() if u.email else "User")
            role = meta.get("role", "aspirant")
            if default_admin_email and u.email and u.email.lower() == default_admin_email.lower():
                role = "admin"

            district = meta.get("district", "Tamil Nadu")

            profile_record = {
                "id": u.id,
                "email": u.email,
                "full_name": full_name,
                "role": role,
                "district": district,
                "state": "Tamil Nadu",
                "profile_data": {},
                "is_active": True
            }
            admin_client.table("profiles").upsert(profile_record, on_conflict="id").execute()

            if role == "aspirant":
                admin_client.table("journeys").upsert({
                    "aspirant_id": u.id,
                    "title": f"{full_name}'s Enterprise Journey",
                    "business_type": "Entrepreneurship",
                    "stage": "idea",
                    "status": "active"
                }, on_conflict="aspirant_id").execute()

                admin_client.table("relationships").upsert({
                    "aspirant_id": u.id,
                    "status": "active"
                }, on_conflict="aspirant_id").execute()

            results["backfilled"] += 1
        except Exception as e:
            results["errors"].append({"email": u.email, "error": str(e)})

    return results

def promote_user_to_admin(email: str) -> Tuple[bool, Optional[str]]:
    """Promotes an existing user profile to 'admin' role in Supabase."""
    clean_email = email.strip().lower()
    if not clean_email:
        return False, "Email is required."

    if get_data_backend() == "sqlite":
        db = get_local_db()
        p = db.get_profile_by_email(clean_email)
        if not p:
            return False, f"User {clean_email} not found in local database."
        p["role"] = "admin"
        db.upsert_profile(p)
        return True, None

    admin_client = get_supabase_admin_client()
    if not admin_client:
        return False, "Supabase admin client unavailable."

    try:
        res = admin_client.table("profiles").update({"role": "admin"}).eq("email", clean_email).execute()
        if res.data and len(res.data) > 0:
            return True, None
        return False, f"No profile found with email '{clean_email}' in Supabase database."
    except Exception as e:
        return False, f"Promotion failed: {e}"

def logout_user():
    """Clears Supabase session and resets Streamlit session state."""
    client = get_supabase_client()
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass

    for key in ["user", "user_id", "role", "sb_access_token", "sb_refresh_token", "selected_aspirant_id", "supabase_client", "auth_mode"]:
        st.session_state.pop(key, None)
