"""
app.py — Main Application Router & Entrypoint for FULCRUM-INDIA (Cluster A)
==========================================================================
Institutional Core Relationship, Profile, Journey & Scheme Intelligence System.
Lightweight, secure, and maintainable Streamlit application backed by Supabase.

UI/UX & Governance:
- Clean Light / Institutional Login Surface (White theme, Avenir typography)
- Hidden technical multipage sidebar during login state
- Dedicated, role-specific application navigation post-authentication
- Zero exposure of internal Python filenames or developer diagnostic text
- Role-based access control enforcing strict administrative authority
"""

import streamlit as st
import os
import sys

# Ensure current directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Self-healing database check at entrypoint (guarantees zero missing-column crashes on fresh or legacy container disks)
import sqlite3
try:
    _db_path = os.path.join(current_dir, "cluster_a.db")
    if os.path.exists(_db_path):
        _conn = sqlite3.connect(_db_path)
        _cur = _conn.cursor()
        _cur.execute("PRAGMA table_info(schemes)")
        _cols = [c[1] for c in _cur.fetchall()]
        if "display_order" not in _cols and len(_cols) > 0:
            _cur.execute("ALTER TABLE schemes ADD COLUMN display_order INTEGER DEFAULT 9999")
            _conn.commit()
        _conn.close()
except Exception:
    pass

# Note: importlib.reload loop removed — it was resetting module singletons on
# every Streamlit rerun, corrupting rendering state and causing ghost login UI.

# Page configuration
st.set_page_config(
    page_title="FULCRUM-INDIA | Enterprise Guidance System",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

from services.auth import logout_user, get_supabase_client
from services.local_db import get_local_db
from views.login import render_login_page
from views.aspirant import render_aspirant_portal
from views.guide import render_guide_portal
from views.sme import render_sme_portal
from views.admin import render_admin_portal

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS INJECTION & TYPOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────
def inject_global_styles(is_logged_in: bool, role: str = None):
    # Hide Streamlit technical multipage navigation always
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* Strictly suppress Streamlit internal multipage nav and file names */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Clean Streamlit chrome elements without hiding sidebar toggle button */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    header [data-testid="stToolbarActions"],
    header [data-testid="stStatusWidget"],
    header [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Set clean institutional typography - NEVER target span or [class*="css"] with !important */
    html, body, .stApp, h1, h2, h3, h4, h5, h6, p, label, input, textarea, select {
        font-family: 'Avenir Next', 'Avenir', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* STRICTLY PROTECT Streamlit expander toggle icon from printing 'keyboard_arrow_right' */
    [data-testid="stExpanderToggleIcon"] {
        font-size: 0px !important;
        line-height: 0 !important;
        color: transparent !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 18px !important;
        height: 18px !important;
    }
    [data-testid="stExpanderToggleIcon"] * {
        display: none !important;
    }
    [data-testid="stExpanderToggleIcon"]::after {
        content: "▶" !important;
        font-size: 11px !important;
        color: #64748B !important;
        display: inline-block !important;
        transition: transform 0.2s ease !important;
    }
    details[open] [data-testid="stExpanderToggleIcon"]::after {
        transform: rotate(90deg) !important;
        color: #2563EB !important;
    }

    /* Additional Icon protection for Material Symbols */
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-icons {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons", sans-serif !important;
        font-feature-settings: "liga" 1 !important;
        display: inline-block !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not is_logged_in:
        # For login state: completely collapse & hide sidebar and its toggle button
        st.markdown("""
        <style>
        section[data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        [data-testid="stExpandSidebarButton"],
        button[kind="header"] {
            display: none !important;
            visibility: hidden !important;
        }
        .main .block-container {
            max-width: 900px !important;
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # For authenticated state: professional institutional clean light theme with dark sidebar
        st.markdown("""
        <style>
        /* Base page background and typography colors */
        .stApp {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }

        /* High-contrast headings and body in main canvas */
        .main .block-container {
            max-width: 1320px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
        }

        .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
            color: #0F172A !important;
            font-family: 'Avenir Next', 'Avenir', sans-serif !important;
        }

        .main p, .main .stMarkdown, .main .stMarkdown p {
            color: #1E293B !important;
        }

        .main label, .main label p {
            color: #0F172A !important;
            font-weight: 600 !important;
        }

        /* High contrast inputs */
        .stTextInput input, .stTextArea textarea {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }

        /* Dedicated Dark Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #0d1322 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
            display: block !important;
            visibility: visible !important;
        }

        section[data-testid="stSidebar"] * {
            color: #E2E8F0;
        }

        section[data-testid="stSidebar"] .stMarkdown p {
            color: #cbd5e1;
        }

        /* Prominent Sidebar Toggle Button when sidebar is collapsed */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"] {
            display: flex !important;
            visibility: visible !important;
            position: fixed !important;
            top: 0.75rem !important;
            left: 0.75rem !important;
            z-index: 99999 !important;
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            padding: 6px 10px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12) !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stExpandSidebarButton"]:hover {
            background-color: #F1F5F9 !important;
            border-color: #94A3B8 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18) !important;
        }
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] span,
        [data-testid="stSidebarCollapsedControl"] *,
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stExpandSidebarButton"] span,
        [data-testid="stExpandSidebarButton"] * {
            fill: #0F172A !important;
            color: #0F172A !important;
        }

        /* Sidebar Close Button inside sidebar */
        [data-testid="stSidebarCollapseButton"] {
            color: #E2E8F0 !important;
            background: rgba(255, 255, 255, 0.08) !important;
            border-radius: 6px !important;
        }
        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebarCollapseButton"] * {
            fill: #E2E8F0 !important;
            color: #E2E8F0 !important;
        }

        /* Role-specific tab navigation - Institutional Clean Light Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F1F5F9 !important;
            padding: 6px;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
            margin-bottom: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            border-radius: 8px;
            color: #475569 !important;
            font-size: 0.88rem;
            font-weight: 600;
            padding: 0 18px;
            background-color: transparent !important;
            border: none !important;
            transition: all 0.15s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #0F172A !important;
            background-color: rgba(255, 255, 255, 0.7) !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2563EB !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
        }
        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span {
            color: #FFFFFF !important;
        }

        /* Institutional Expanders */
        div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 10px !important;
            margin-bottom: 0.75rem !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        }
        div[data-testid="stExpander"] details {
            border: none !important;
            background-color: #FFFFFF !important;
            border-radius: 10px !important;
        }
        div[data-testid="stExpander"] details summary {
            padding: 0.85rem 1.1rem !important;
            font-weight: 600 !important;
            color: #0F172A !important;
            border-radius: 10px !important;
        }
        div[data-testid="stExpander"] details summary:hover {
            background-color: #F8FAFC !important;
        }
        div[data-testid="stExpander"] details summary p,
        div[data-testid="stExpander"] details summary span:not([data-testid="stExpanderToggleIcon"]) {
            color: #0F172A !important;
            font-weight: 600 !important;
        }

        /* Primary Buttons */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.88rem;
            padding: 0.5rem 1.25rem;
            transition: all 0.15s ease-in-out;
        }
        button[kind="primary"] {
            background: #2563eb !important;
            border: 1px solid #1d4ed8 !important;
            color: #ffffff !important;
        }
        button[kind="primary"]:hover {
            background: #1d4ed8 !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        }

        /* Modal Dialog Styling (Modern, Clean, Spacious) */
        div[data-testid="stDialog"] {
            border-radius: 16px !important;
            box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25) !important;
            border: 1px solid #E2E8F0 !important;
        }
        div[data-testid="stDialog"] [data-testid="stDialogHeader"] {
            padding-bottom: 10px !important;
            border-bottom: 1px solid #E2E8F0 !important;
        }
        div[data-testid="stDialog"] [data-testid="stDialogHeader"] h2,
        div[data-testid="stDialog"] [data-testid="stDialogHeader"] span {
            color: #0F172A !important;
            font-weight: 800 !important;
        }
        </style>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Initialize session state keys
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "nav_section" not in st.session_state:
        st.session_state.nav_section = "Dashboard"

    user = st.session_state.user
    role = st.session_state.role
    is_logged_in = bool(user and role)

    inject_global_styles(is_logged_in, role)

    # ─────────────────────────────────────────────────────────────────────────
    # AUTHENTICATED SIDEBAR NAVIGATION (Our Own Role-Specific Navigation)
    # ─────────────────────────────────────────────────────────────────────────
    if is_logged_in:
        with st.sidebar:
            st.markdown("""
            <div style="padding: 0.5rem 0 1rem; border-bottom: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.65rem; font-weight: 800; letter-spacing: 1.5px; color: #60a5fa; text-transform: uppercase; margin-bottom: 2px;">
                    Enterprise System
                </div>
                <div style="font-size: 1.35rem; font-weight: 900; letter-spacing: -0.5px; color: #ffffff;">
                    FULCRUM-INDIA
                </div>
                <div style="font-size: 0.74rem; color: #94a3b8; line-height: 1.3; margin-top: 2px;">
                    Core Relationship & Journey System
                </div>
            </div>
            """, unsafe_allow_html=True)

            # User Profile Badge
            role_badges = {
                "aspirant": {"label": "Aspirant", "bg": "rgba(59, 130, 246, 0.2)", "color": "#60a5fa"},
                "guide": {"label": "Verified Guide", "bg": "rgba(16, 185, 129, 0.2)", "color": "#34d399"},
                "sme": {"label": "Domain SME", "bg": "rgba(14, 165, 233, 0.2)", "color": "#38bdf8"},
                "admin": {"label": "Program Admin", "bg": "rgba(236, 72, 153, 0.2)", "color": "#f472b6"}
            }
            rb = role_badges.get(role, {"label": role.upper(), "bg": "rgba(255,255,255,0.1)", "color": "#fff"})

            st.markdown(f"""
            <div style="background: rgba(17, 24, 39, 0.75); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.85rem; margin-top: 1rem; margin-bottom: 1rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Current User</div>
                <div style="font-size: 0.95rem; font-weight: 700; color: #f8fafc; margin-top: 2px;">
                    {user.get('full_name', 'User')}
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 1px; word-break: break-all;">
                    {user.get('email', '')}
                </div>
                <div style="margin-top: 0.5rem; display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700; background: {rb['bg']}; color: {rb['color']}; text-transform: uppercase;">
                        {rb['label']}
                    </span>
                    <span style="font-size: 0.72rem; color: #94a3b8;">
                        📍 {user.get('district', 'Tamil Nadu')}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Role-Specific Navigation Links
            st.markdown("<div style='font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 0.5rem;'>Navigation</div>", unsafe_allow_html=True)

            if role == "aspirant":
                nav_items = [
                    "📊 Dashboard Overview",
                    "👤 My Profile",
                    "🎬 My Journey",
                    "🤝 My Mentors",
                    "🏦 Scheme Matches",
                    "💬 Help / Support"
                ]
            elif role == "guide":
                nav_items = [
                    "📊 Dashboard Overview",
                    "👥 My Assigned Aspirants",
                    "🎬 Mentorship Workspace"
                ]
            elif role == "sme":
                nav_items = [
                    "📊 Dashboard Overview",
                    "🎯 My Assigned Cases",
                    "🎬 Domain Advisory Workspace"
                ]
            elif role == "admin":
                nav_items = [
                    "📊 Command Metrics",
                    "👥 Aspirants Directory",
                    "🧭 Guides Management",
                    "🔬 SMEs Management",
                    "🤝 Mentorship Assignments",
                    "💬 Help Requests Queue",
                    "🏛️ Scheme Catalogue"
                ]
            else:
                nav_items = ["Dashboard"]

            for item in nav_items:
                st.markdown(f"<div style='font-size: 0.85rem; color: #cbd5e1; padding: 6px 10px; border-radius: 6px; margin-bottom: 3px; background: rgba(255,255,255,0.03);'>✓ {item}</div>", unsafe_allow_html=True)

            st.write("")
            if st.button("🚪 Logout", use_container_width=True, key="btn_sidebar_logout"):
                logout_user()
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # ROUTING LOGIC (Role Portals)
    # ─────────────────────────────────────────────────────────────────────────
    if not is_logged_in:
        render_login_page()
    elif role == "aspirant":
        render_aspirant_portal(user)
    elif role == "guide":
        render_guide_portal(user)
    elif role == "sme":
        render_sme_portal(user)
    elif role == "admin":
        render_admin_portal(user)
    else:
        st.error(f"Unrecognized user role: '{role}'. Please contact support.")
        if st.button("Reset Session"):
            logout_user()
            st.rerun()

if __name__ == "__main__":
    main()
