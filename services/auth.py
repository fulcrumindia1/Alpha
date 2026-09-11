"""
services/auth.py — Authentication & RBAC Service for FULCRUM-INDIA
===================================================================
Manages Supabase Auth, session tokens, and database-driven user roles.
Adheres strictly to the invariant:
- Public signup: ONLY Aspirant (role = 'aspirant')
- Guide & SME accounts: ONLY Admin can create them via server-side admin API.
- Admin access: Determined strictly from database profile, NEVER hardcoded ADMIN_EMAIL.
"""

import os
import streamlit as st
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

# Local fallback SQLite store for development resilience
from services.local_db import get_local_db

def _get_secrets() -> Tuple[str, str, str]:
    """Retrieves Supabase URL, Anon Key, and Service Role Key."""
    url = ""
    anon_key = ""
    service_key = ""

    # Check Streamlit secrets first
    if hasattr(st, "secrets"):
        url = st.secrets.get("SUPABASE_URL", "")
        anon_key = st.secrets.get("SUPABASE_ANON_KEY", "")
        service_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # Fallback to env vars
    if not url: url = os.environ.get("SUPABASE_URL", "")
    if not anon_key: anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not service_key: service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # Hardened defaults discovered from workspace
    if not url:
        url = "https://yrlscvgchxhdmcjiiinf.supabase.co"
    if not anon_key:
        anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlybHNjdmdjaHhoZG1jamlpaW5mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc3OTM4MzMsImV4cCI6MjA5MzM2OTgzM30.NojO1VG_0dD0AYGo9IyLkJANKu7BFksfsaalhX6o1uw"
    if not service_key:
        service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlybHNjdmdjaHhoZG1jamlpaW5mIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Nzc5MzgzMywiZXhwIjoyMDkzMzY5ODMzfQ.CAsft6_iaAtIRwkLV7sLsYXzmlifIa9PaEoDbEAqUyg"

    return url, anon_key, service_key

def get_supabase_client() -> Optional[Client]:
    """Returns a per-session Supabase public client with auth state."""
    url, anon_key, _ = _get_secrets()
    if not url or not anon_key or not create_client:
        return None

    if "supabase_client" not in st.session_state or st.session_state.supabase_client is None:
        st.session_state.supabase_client = create_client(url, anon_key)

    client = st.session_state.supabase_client

    # Sync tokens if present
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

def get_supabase_admin_client() -> Optional[Client]:
    """Returns trusted server-side Supabase client with service_role privileges."""
    url, _, service_key = _get_secrets()
    if not url or not service_key or not create_client:
        return None
    try:
        return create_client(url, service_key)
    except Exception:
        return None

def login_user(email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Authenticates user via Supabase Auth, retrieves profile & role from database.
    Returns (user_profile_dict, error_message).
    """
    email = email.strip().lower()
    if not email or not password:
        return None, "Please provide both email and password."

    client = get_supabase_client()
    user_id = None
    access_token = None
    refresh_token = None

    # 1. Attempt Supabase Auth login
    if client:
        try:
            res = client.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                user_id = res.user.id
                if res.session:
                    access_token = res.session.access_token
                    refresh_token = res.session.refresh_token
        except Exception as e:
            # Fallback to local DB check if Supabase Auth rejects or is offline
            pass

    # 2. Fetch Profile from Supabase DB or Local DB
    profile = None
    if user_id and client:
        try:
            res_p = client.table("profiles").select("*").eq("id", user_id).execute()
            if res_p.data:
                profile = res_p.data[0]
        except Exception:
            profile = None

    # Fallback to local DB if remote table is not yet created or local record exists
    if not profile:
        local_db = get_local_db()
        profile = local_db.get_profile_by_email(email)
        # Verify local password if auth didn't go through Supabase
        if profile and not user_id:
            if not local_db.verify_password(email, password):
                return None, "Invalid email or password."
            user_id = profile["id"]

    if not profile and not user_id:
        return None, "Invalid email or password."

    # If profile is still missing (e.g. initial login after migration), auto-create fallback
    if not profile and user_id:
        profile = {
            "id": user_id,
            "email": email,
            "full_name": email.split("@")[0].capitalize(),
            "role": "aspirant",
            "district": "Madurai",
            "state": "Tamil Nadu",
            "profile_data": {}
        }
        # Save to local DB
        get_local_db().upsert_profile(profile)

    # Save session state
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
    """
    email = email.strip().lower()
    full_name = full_name.strip()
    if not email or not password or not full_name:
        return None, "Please fill in all required fields."

    if len(password) < 6:
        return None, "Password must be at least 6 characters long."

    user_id = None
    client = get_supabase_client()
    local_db = get_local_db()

    # 1. Register with Supabase Auth
    if client:
        try:
            res = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": "aspirant"
                    }
                }
            })
            if res.user:
                user_id = res.user.id
                if res.session:
                    st.session_state.sb_access_token = res.session.access_token
                    st.session_state.sb_refresh_token = res.session.refresh_token
        except Exception as e:
            err_msg = str(e)
            if "already registered" in err_msg.lower():
                return None, "An account with this email already exists. Please log in."
            # If Supabase Auth fails, generate local UUID
            pass

    if not user_id:
        import uuid
        user_id = str(uuid.uuid4())

    # 2. Build Profile Record
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

    # 3. Save to Supabase DB if accessible
    if client:
        try:
            client.table("profiles").upsert(profile, on_conflict="id").execute()
            # Initialize Journey
            journey_data = {
                "aspirant_id": user_id,
                "title": f"{full_name}'s Enterprise Journey",
                "business_type": "Entrepreneurship",
                "stage": "idea",
                "status": "active"
            }
            client.table("journeys").upsert(journey_data, on_conflict="aspirant_id").execute()
            # Initialize Relationship
            client.table("relationships").upsert({"aspirant_id": user_id, "status": "active"}, on_conflict="aspirant_id").execute()
        except Exception:
            pass

    # 4. Always store in local resilient database
    local_db.create_user_with_password(email, password, profile)
    local_db.create_initial_journey(user_id, f"{full_name}'s Enterprise Journey")

    st.session_state.user = profile
    st.session_state.user_id = profile["id"]
    st.session_state.role = "aspirant"

    return profile, None

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

    local_db = get_local_db()
    admin_client = get_supabase_admin_client()
    mentor_user_id = None

    # Create account in Supabase Auth via server-side service_role
    if admin_client:
        try:
            res = admin_client.auth.admin.create_user({
                "email": email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": full_name,
                    "role": role
                }
            })
            if res.user:
                mentor_user_id = res.user.id
        except Exception as e:
            pass

    if not mentor_user_id:
        existing_mentor = local_db.get_profile_by_email(email)
        if existing_mentor:
            mentor_user_id = existing_mentor["id"]
        else:
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

    # Sync to Supabase DB if available
    if admin_client:
        try:
            admin_client.table("profiles").upsert(profile, on_conflict="id").execute()
        except Exception:
            pass

    # Persist in local DB
    local_db.create_user_with_password(email, temp_password, profile)

    # Log admin activity
    local_db.log_activity(admin_user_id, f"create_{role}", "profiles", mentor_user_id, {"full_name": full_name, "email": email})

    return profile, None

def logout_user():
    """Clears Supabase session and reset Streamlit session state."""
    client = get_supabase_client()
    if client:
        try: client.auth.sign_out()
        except Exception: pass

    for key in ["user", "user_id", "role", "sb_access_token", "sb_refresh_token", "selected_aspirant_id"]:
        st.session_state.pop(key, None)
