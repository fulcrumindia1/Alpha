"""
views/login.py — Institutional Light Login & Aspirant Onboarding for FULCRUM-INDIA
==================================================================================
Design Guidelines:
- Clean Light / White Institutional Design (Refined, Modern, Calm, Trustworthy)
- Typography: Avenir Next / Avenir with clean system fallbacks
- Button Styling: Brand Royal Blue (#2563EB) with crisp white text, high contrast
- Centered surface with clear visual hierarchy
- Single public self-registration flow strictly for Aspirants (role = 'aspirant')
- Zero public registration for Guides, SMEs, or Admins
- Built-in Demo Test Credentials and 1-Click Role Quick Fill
"""

import streamlit as st
from services.auth import login_user, signup_aspirant

def render_login_page():
    # Inject Institutional Light Theme CSS specifically for the login surface
    st.markdown("""
    <style>
    /* Full Page Background - Calm Institutional Neutral */
    .stApp {
        background-color: #F8FAFC !important;
        background-image: none !important;
    }

    /* Hide Streamlit technical multipage sidebar navigation and toggle controls */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    section[data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stExpandSidebarButton"],
    button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Typography - Avenir Next / Avenir with elegant system fallbacks */
    html, body, .stApp, h1, h2, h3, h4, h5, h6, p, label, input, textarea, select {
        font-family: 'Avenir Next', 'Avenir', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #1E293B;
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

    /* Centered Login Card Container */
    .auth-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 2.5rem 2.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03), 0 20px 25px -5px rgba(0, 0, 0, 0.04);
        margin: 1.5rem auto 2.5rem;
        max-width: 480px;
    }

    .auth-brand-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #2563EB;
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        padding: 4px 12px;
        border-radius: 20px;
        margin-bottom: 0.75rem;
    }

    .auth-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0F172A !important;
        margin: 0 0 0.4rem 0;
        line-height: 1.15;
    }

    .auth-subtitle {
        font-size: 0.9rem;
        font-weight: 500;
        color: #64748B !important;
        line-height: 1.45;
        margin-bottom: 1.75rem;
    }

    /* Light Theme Input Styling */
    .stTextInput > div > div > input {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 6px !important;
        font-size: 0.92rem !important;
        padding: 0.6rem 0.85rem !important;
        transition: all 0.15s ease-in-out;
    }
    .stTextInput > div > div > input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        background-color: #FFFFFF !important;
    }

    .stTextInput label {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
        letter-spacing: 0.01em;
        margin-bottom: 4px;
    }

    /* Brand Blue Login Button - High Contrast & Refined */
    .stButton > button {
        background-color: #2563EB !important;
        background-image: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #1D4ED8 !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.03em !important;
        padding: 0.65rem 1.25rem !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #1D4ED8 !important;
        background-image: none !important;
        border-color: #1E40AF !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2) !important;
    }
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Tabs Styling - Blue Active Indicator */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 4px !important;
        gap: 4px !important;
        margin-bottom: 1.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px !important;
        border-radius: 6px !important;
        color: #64748B !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2563EB !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    }
    [data-baseweb="tab-highlight"] {
        background-color: #2563EB !important;
    }

    /* Footer Trust Mark */
    .auth-footer {
        text-align: center;
        margin-top: 1.75rem;
        padding-top: 1.25rem;
        border-top: 1px solid #F1F5F9;
        font-size: 0.78rem;
        color: #94A3B8;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)

    # Centered Container Layout
    col_l, col_center, col_r = st.columns([1, 1.4, 1])

    with col_center:
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; margin-bottom: 1.25rem;">
            <div class="auth-brand-badge">Institutional Enterprise System</div>
            <h1 class="auth-title">FULCRUM-INDIA</h1>
            <div class="auth-subtitle">
                Core Relationship, Profile, Journey & Scheme Intelligence System
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Sign In", "Create Aspirant Account"], key="auth_surface_tabs")

        # ─────────────────────────────────────────────────────────────
        # TAB 1: LOGIN SURFACE
        # ─────────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("<p style='font-size: 0.84rem; color: #64748B; margin-bottom: 1.25rem;'>Enter your credentials to access your verified dashboard.</p>", unsafe_allow_html=True)
            
            login_email = st.text_input(
                "Email Address",
                placeholder="name@domain.in",
                key="input_login_email"
            )
            login_password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="input_login_pwd"
            )

            st.write("")
            if st.button("LOGIN", use_container_width=True, key="btn_do_login"):
                if login_email and login_password:
                    profile, err = login_user(login_email, login_password)
                    if profile:
                        st.rerun()
                    else:
                        st.error(err or "Invalid credentials. Please verify your email and password.")
                else:
                    st.warning("Please enter your email and password.")

            # Clear Credentials Reference Box
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.85rem 1rem; margin-top: 1.5rem; font-size: 0.8rem;">
                <div style="font-weight: 700; color: #334155; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 6px;">
                    <span>📋 Verified Test Accounts:</span>
                </div>
                <div style="color: #475569; line-height: 1.55;">
                    <div>• <strong>Admin:</strong> <code style="color:#2563EB;">admin@fulcrum.in</code> | <code>Admin@123</code></div>
                    <div>• <strong>Aspirant:</strong> <code style="color:#2563EB;">ravi.kumar@milletfoods.in</code> | <code>Aspirant@123</code></div>
                    <div>• <strong>Guide:</strong> <code style="color:#2563EB;">rajendran@fulcrum.in</code> | <code>Welcome@2026</code></div>
                    <div>• <strong>SME:</strong> <code style="color:#2563EB;">kumar.sme@fulcrum.in</code> | <code>Welcome@2026</code></div>
                </div>
            </div>

            <div style="text-align: center; margin-top: 1.25rem; font-size: 0.82rem; color: #64748B;">
                <div style="margin-bottom: 0.5rem;">
                    Forgot Password? Contact your administrator at <span style="font-weight: 600; color: #334155;">admin@fulcrum.in</span>
                </div>
                <div style="color: #94A3B8; font-size: 0.76rem;">
                    Authorized access only · Aspirants, Guides, SMEs & Program Administrators
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ─────────────────────────────────────────────────────────────
        # TAB 2: PUBLIC ASPIRANT SIGNUP SURFACE (Aspirants Only)
        # ─────────────────────────────────────────────────────────────
        with tab_signup:
            st.markdown("<p style='font-size: 0.84rem; color: #64748B; margin-bottom: 1.25rem;'>Register as an entrepreneur to access mentorship and scheme intelligence.</p>", unsafe_allow_html=True)

            s_name = st.text_input("Full Name", placeholder="Ravi Kumar", key="signup_name")
            s_email = st.text_input("Work / Personal Email", placeholder="ravi.kumar@milletfoods.in", key="signup_email")
            
            c_ph, c_dist = st.columns(2)
            with c_ph:
                s_phone = st.text_input("Mobile Number", placeholder="9876543210", key="signup_phone")
            with c_dist:
                s_dist = st.selectbox("District (Tamil Nadu)", [
                    "Madurai", "Chennai", "Coimbatore", "Tiruchirappalli", "Salem",
                    "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul",
                    "Thanjavur", "Ranipet", "Virudhunagar", "Karur", "Other"
                ], key="signup_district")

            # If "Other" is selected, show a text input to specify the actual district/city/state
            s_final_district = s_dist
            if s_dist == "Other":
                s_other_dist = st.text_input("Specify District / City / State *", placeholder="e.g. Kanyakumari, Namakkal, Bengaluru (Karnataka)", key="signup_other_district")
                if s_other_dist and s_other_dist.strip():
                    s_final_district = s_other_dist.strip()

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                s_pwd = st.text_input("Create Password", type="password", placeholder="••••••••", key="signup_pwd")
            with c_p2:
                s_pwd_confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••", key="signup_pwd2")

            st.write("")
            if st.button("CREATE ASPIRANT ACCOUNT", use_container_width=True, key="btn_do_signup"):
                if not s_name or not s_email or not s_pwd:
                    st.error("Please fill in all mandatory fields.")
                elif s_pwd != s_pwd_confirm:
                    st.error("Passwords do not match.")
                elif len(s_pwd) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif s_dist == "Other" and not s_other_dist.strip():
                    st.error("Please specify your district / city / state.")
                else:
                    profile, err = signup_aspirant(
                        email=s_email,
                        password=s_pwd,
                        full_name=s_name,
                        phone=s_phone,
                        district=s_final_district
                    )
                    if profile:
                        st.rerun()
                    else:
                        st.error(err or "Failed to create account. Email may already be in use.")

            st.markdown("""
            <div style="text-align: center; margin-top: 1.25rem; font-size: 0.78rem; color: #94A3B8;">
                Note: Mentors (Guides and Subject Matter Experts) are provisioned exclusively by Program Administration.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="auth-footer">
            FULCRUM-INDIA Enterprise Guidance System · Cluster A<br>
            Protected by Row Level Security (RLS) & Verified RBAC
        </div>
        """, unsafe_allow_html=True)
