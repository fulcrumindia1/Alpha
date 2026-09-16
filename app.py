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

# Self-healing database check at entrypoint — runs ONCE per session
# (guarantees zero missing-column crashes on fresh or legacy container disks)
import sqlite3
if not st.session_state.get("_sqlite_schema_healed"):
    try:
        from services.local_db import get_local_db
        get_local_db()
    except Exception as _e:
        print(f"[SchemaHealing] Notice: {_e}")
    st.session_state._sqlite_schema_healed = True

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
        button[kind="header"],
        [data-testid="stDeployButton"],
        .stAppDeployButton,
        #MainMenu,
        footer {
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
        /* Keep stToolbar visible so Streamlit 1.56+ stExpandSidebarButton can render */
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: visible !important;
            background: transparent !important;
        }

        /* Hide technical clutter in toolbar and footer */
        [data-testid="stDeployButton"],
        .stAppDeployButton,
        [data-testid="stToolbarActions"],
        [data-testid="stStatusWidget"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
        }

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

        /* Sidebar Expander & Notification Center — Dark Theme Seamless Integration */
        section[data-testid="stSidebar"] [data-testid="stExpander"],
        section[data-testid="stSidebar"] details {
            background-color: #111827 !important;
            background: #111827 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            margin-bottom: 0.6rem !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
        section[data-testid="stSidebar"] details > summary {
            background-color: #172138 !important;
            background: #172138 !important;
            color: #F8FAFC !important;
            border-radius: 9px !important;
            border: none !important;
            padding: 0.55rem 0.85rem !important;
            font-weight: 700 !important;
            cursor: pointer !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover,
        section[data-testid="stSidebar"] details > summary:hover {
            background-color: #1E293B !important;
            background: #1E293B !important;
            color: #60A5FA !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
        section[data-testid="stSidebar"] details > summary svg,
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
        section[data-testid="stSidebar"] details > summary span,
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
        section[data-testid="stSidebar"] details > summary p {
            color: #F8FAFC !important;
            fill: #F8FAFC !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"],
        section[data-testid="stSidebar"] details > div:not(summary) {
            background-color: #111827 !important;
            background: #111827 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding: 0.75rem 0.55rem !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] .stCaption {
            color: #94A3B8 !important;
        }

        /* Notification Action Buttons inside Expander (Mark All / Dismiss) */
        section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button,
        section[data-testid="stSidebar"] details div.stButton > button {
            background: rgba(37, 99, 235, 0.18) !important;
            border: 1px solid rgba(59, 130, 246, 0.45) !important;
            border-radius: 6px !important;
            padding: 0.35rem 0.65rem !important;
            font-weight: 600 !important;
            font-size: 0.76rem !important;
            letter-spacing: 0.2px !important;
            color: #93C5FD !important;
            margin: 0.2rem 0 0.4rem 0 !important;
            width: 100% !important;
            box-shadow: none !important;
            transform: none !important;
            transition: all 0.2s ease !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button *,
        section[data-testid="stSidebar"] details div.stButton > button * {
            color: #93C5FD !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover,
        section[data-testid="stSidebar"] details div.stButton > button:hover {
            background: rgba(37, 99, 235, 0.35) !important;
            border-color: #60A5FA !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover *,
        section[data-testid="stSidebar"] details div.stButton > button:hover * {
            color: #FFFFFF !important;
        }

        /* Sidebar Logout Button — Dark Danger Style */
        section[data-testid="stSidebar"] div.stButton > button {
            background: rgba(239, 68, 68, 0.08) !important;
            border: 1px solid rgba(239, 68, 68, 0.28) !important;
            border-radius: 8px !important;
            padding: 0.55rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.86rem !important;
            letter-spacing: 0.3px !important;
            transition: all 0.2s ease-in-out !important;
            margin-top: 0.5rem !important;
        }

        section[data-testid="stSidebar"] div.stButton > button,
        section[data-testid="stSidebar"] div.stButton > button * {
            color: #F87171 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: rgba(239, 68, 68, 0.22) !important;
            border-color: #EF4444 !important;
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.25) !important;
            transform: translateY(-1px);
        }

        section[data-testid="stSidebar"] div.stButton > button:hover,
        section[data-testid="stSidebar"] div.stButton > button:hover * {
            color: #FFFFFF !important;
        }

        section[data-testid="stSidebar"] div.stButton > button:active {
            transform: translateY(0);
            box-shadow: none !important;
        }

        /* Prominent Sidebar Toggle Button when sidebar is collapsed */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"],
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"] button[kind="header"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 0.75rem !important;
            left: 0.75rem !important;
            z-index: 999999 !important;
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 8px !important;
            padding: 6px 10px !important;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12) !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stExpandSidebarButton"]:hover,
        [data-testid="collapsedControl"]:hover,
        header[data-testid="stHeader"] button[kind="header"]:hover {
            background-color: #F1F5F9 !important;
            border-color: #2563EB !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.2) !important;
            transform: translateY(-1px);
        }
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] span,
        [data-testid="stSidebarCollapsedControl"] *,
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stExpandSidebarButton"] span,
        [data-testid="stExpandSidebarButton"] *,
        [data-testid="collapsedControl"] svg,
        [data-testid="collapsedControl"] span,
        [data-testid="collapsedControl"] *,
        header[data-testid="stHeader"] button[kind="header"] svg,
        header[data-testid="stHeader"] button[kind="header"] span,
        header[data-testid="stHeader"] button[kind="header"] * {
            fill: #0F172A !important;
            color: #0F172A !important;
        }

        /* Sidebar Close Button inside open sidebar */
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            color: #E2E8F0 !important;
            background: rgba(255, 255, 255, 0.12) !important;
            border-radius: 6px !important;
            cursor: pointer !important;
        }
        [data-testid="stSidebarCollapseButton"]:hover {
            background: rgba(255, 255, 255, 0.22) !important;
        }
        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stSidebarCollapseButton"] span,
        [data-testid="stSidebarCollapseButton"] * {
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
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
            <div style="background: rgba(17, 24, 39, 0.75); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.85rem; margin-top: 1rem; margin-bottom: 0.75rem;">
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

            # ─────────────────────────────────────────────────────────────────
            # IN-APP NOTIFICATION CENTER (Universal & Mobile-Friendly)
            # ─────────────────────────────────────────────────────────────────
            from services.notifications import get_unread_count, list_notifications, mark_as_read, mark_all_as_read
            user_id = user.get("id")
            unread_count = get_unread_count(user_id) if user_id else 0

            notif_expander_title = f"🔔 Notifications ({unread_count} New)" if unread_count > 0 else "🔔 Notifications"
            with st.expander(notif_expander_title, expanded=(unread_count > 0)):
                if user_id:
                    user_notifs = list_notifications(user_id)
                    if not user_notifs:
                        st.caption("No notifications yet.")
                    else:
                        if unread_count > 0:
                            if st.button("Mark all as read", key="btn_notif_mark_all", use_container_width=True):
                                mark_all_as_read(user_id)
                                st.rerun()
                        for n in user_notifs[:6]:
                            is_unread = not n.get("is_read")
                            bg_style = "background: rgba(37, 99, 235, 0.22); border: 1px solid rgba(59, 130, 246, 0.45); border-left: 3.5px solid #3b82f6;" if is_unread else "background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08);"
                            title_color = "#93C5FD" if is_unread else "#E2E8F0"
                            date_str = (n.get("created_at") or "")[:16].replace("T", " ")
                            st.markdown(f"""
                            <div style="{bg_style} border-radius: 7px; padding: 7px 10px; margin-bottom: 6px;">
                                <div style="font-weight: 700; color: {title_color}; font-size: 0.8rem; line-height: 1.3;">{'🔵 ' if is_unread else ''}{n.get('title', '')}</div>
                                <div style="color: #CBD5E1; margin-top: 3px; font-size: 0.74rem; line-height: 1.35;">{n.get('message', '')}</div>
                                <div style="color: #94A3B8; font-size: 0.68rem; margin-top: 4px;">{date_str}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if is_unread:
                                if st.button("✓ Dismiss", key=f"btn_dismiss_{n['id']}", help="Mark as read", use_container_width=True):
                                    mark_as_read(n["id"], user_id)
                                    st.rerun()

            # Role-Specific Navigation Links
            st.markdown("<div style='font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-top: 0.5rem; margin-bottom: 0.5rem;'>Navigation</div>", unsafe_allow_html=True)

            if role == "aspirant":
                nav_items = [
                    "📊 Dashboard Overview",
                    "👤 My Profile",
                    "🎬 My Journey",
                    "🤝 My Mentors",
                    "🏦 Scheme Matches",
                    "🤝 Consult a Guide or SME"
                ]
            elif role == "guide":
                nav_items = [
                    "👥 My Aspirants",
                    "💬 All Consultations Overview",
                    "👤 My Profile"
                ]
            elif role == "sme":
                nav_items = [
                    "👥 My Assigned Cases",
                    "💬 All Consultations Overview",
                    "👤 My Profile"
                ]
            elif role == "admin":
                nav_items = [
                    "📊 Command Metrics",
                    "👥 Aspirants Directory",
                    "🧭 Guides Management",
                    "🔬 SMEs Management",
                    "🤝 Mentorship Assignments",
                    "🏛️ Mentor Inquiries & Directives",
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
    # ROUTING LOGIC (Role Portals) — direct render, no st.empty() wrapper
    # ─────────────────────────────────────────────────────────────────────────
    if not is_logged_in:
        render_login_page()
    else:
        # Check if user was provisioned with a temporary password and must set a permanent password
        user_prof_data = user.get("profile_data") or {}
        if isinstance(user_prof_data, str):
            import json
            try:
                user_prof_data = json.loads(user_prof_data)
            except Exception:
                user_prof_data = {}

        if user_prof_data.get("temp_password_issued") is True:
            st.markdown("""
            <div style="max-width:580px; margin: 2rem auto; background:#FFFFFF; border:1.5px solid #E2E8F0; border-top:4px solid #f59e0b; border-radius:14px; padding:2rem; box-shadow:0 4px 14px rgba(0,0,0,0.06);">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:1rem;">
                    <div style="font-size:2rem;">🔐</div>
                    <div>
                        <h2 style="margin:0; font-size:1.35rem; color:#0F172A;">Action Required: Set Permanent Password</h2>
                        <div style="color:#64748B; font-size:0.88rem; margin-top:2px;">Your account was provisioned with a temporary administrative password.</div>
                    </div>
                </div>
                <p style="color:#334155; font-size:0.92rem; line-height:1.5;">
                    For the security of institutional schemes, mentee dossiers, and administrative workflows, please create a new permanent password before accessing your workspace.
                </p>
            </div>
            """, unsafe_allow_html=True)

            col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
            with col_c2:
                with st.form("form_first_login_pw"):
                    np1 = st.text_input("New Permanent Password *", type="password", placeholder="At least 6 characters", help="Choose a strong password")
                    np2 = st.text_input("Confirm New Password *", type="password", placeholder="Re-type password")
                    if st.form_submit_button("SET PERMANENT PASSWORD & ENTER", type="primary", use_container_width=True):
                        if not np1 or len(np1) < 6:
                            st.error("Password must be at least 6 characters long.")
                        elif np1 != np2:
                            st.error("Passwords do not match. Please re-enter.")
                        else:
                            from services.auth import complete_first_login_password_change
                            ok, err = complete_first_login_password_change(user["id"], np1)
                            if ok:
                                st.success("Permanent password set successfully! Redirecting to workspace...")
                                st.rerun()
                            else:
                                st.error(err or "Failed to update password.")
            return

        # Mobile-friendly banner for unread notifications
        if user and user.get("id"):
            try:
                from services.notifications import get_unread_count
                u_cnt = get_unread_count(user.get("id"))
                if u_cnt > 0:
                    st.info(f"🔔 You have **{u_cnt}** new notification{'s' if u_cnt > 1 else ''}! Review them in the sidebar notification center.")
            except Exception:
                pass

        if role == "aspirant":
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
