"""
pages/guide.py — Guide Dashboard for FULCRUM-INDIA (Cluster A)
=============================================================
Guide Experience:
- 👥 My Aspirants:
  - Select assigned entrepreneur
  - 4 subtabs:
    1. 👤 Profile: Complete Naukri/LinkedIn-style profile & venture breakdown
    2. 🎬 Journey: Full chronological timeline + log mentorship contributions
    3. 🤝 Assigned Mentors: View assigned Guide and SME details
    4. 🏦 Scheme Matches (The Gatekeeper Workspace):
       - Search & filter 170+ master scheme catalogue
       - ⚡ GENERATE evaluation (Score, Match Checklist, Eligibility)
       - View Private Intelligence (🤫 Hidden Agenda, ⚠️ Red Flags)
       - 🚀 RELEASE TO ASPIRANT with custom recommendation note
       - Release history with 📦 Withdraw Release action
- 💬 Help Requests:
  - View support tickets assigned to this Guide
  - Respond and resolve tickets
  - View overdue escalated tickets (>7 days)
"""

import streamlit as st
import html
import inspect
from datetime import date

def _safe_esc(val, default=""):
    """Crash-proof HTML escape that safely handles None, booleans, and non-string types."""
    if val is None:
        return default
    return html.escape(str(val))

from services.relationships import get_assigned_aspirants_for_guide, get_aspirant_mentors, get_assignment_history
from services.profiles import get_profile, update_mentor_profile
from services.journey import get_journey_timeline, add_guide_contribution, soft_delete_event, get_standard_role_label
from services.schemes import (
    list_schemes,
    match_schemes_for_aspirant,
    evaluate_scheme_for_aspirant,
    release_scheme_to_aspirant,
    withdraw_scheme_release,
    get_guide_scheme_releases
)
from services.constants import MASTER_CATEGORY_TYPES, MASTER_STAGES, MASTER_DISTRICTS_TN
from services.help_requests import (
    list_guide_requests,
    guide_respond_request,
    create_mentor_admin_query,
    list_mentor_admin_queries,
    create_mentor_consultation
)
from services.schemes_ui import parse_list_field

def render_guide_portal(user_profile: dict):
    guide_id = user_profile["id"]
    guide_name = user_profile.get("full_name", "Mentor")

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #E2E8F0;">
        <div>
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#059669;">Guide Portal</div>
            <h1 style="font-size:2rem; font-weight:800; margin:0; color:#0F172A;">Welcome, {guide_name}</h1>
            <p style="font-size:0.95rem; color:#475569; margin-top:0.25rem;">
                Dedicated Enterprise Guidance & Scheme Gatekeeper Workspace
            </p>
        </div>
        <div style="text-align:right;">
            <span style="display:inline-block; padding:4px 14px; border-radius:12px; font-size:0.85rem; font-weight:700; background:#ECFDF5; color:#059669; border:1px solid #A7F3D0;">
                Role: Verified Guide
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    main_tabs = st.tabs(["👥 My Aspirants", "💬 All Consultations Overview", "👤 My Profile"])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: MY ASPIRANTS WORKSPACE
    # ─────────────────────────────────────────────────────────────
    with main_tabs[0]:
        assigned_aspirants = get_assigned_aspirants_for_guide(guide_id)

        if not assigned_aspirants:
            st.info("No Aspirants are currently assigned to you. When the Admin assigns an entrepreneur to your roster, they will appear here.")
        else:
            # Selector for which aspirant to advise
            asp_options = {
                a["id"]: f"{a['full_name']} — {a.get('profile_data',{}).get('business',{}).get('business_name','Enterprise')} ({a.get('district', 'Tamil Nadu')})"
                for a in assigned_aspirants
            }
            default_idx = 0
            if st.session_state.get("guide_selected_aspirant") in asp_options:
                default_idx = list(asp_options.keys()).index(st.session_state["guide_selected_aspirant"])

            selected_asp_id = st.selectbox(
                "Select Entrepreneur to Advise",
                list(asp_options.keys()),
                format_func=lambda x: asp_options[x],
                index=default_idx,
                key="guide_asp_select"
            )
            st.session_state["guide_selected_aspirant"] = selected_asp_id

            curr_asp = next((a for a in assigned_aspirants if a["id"] == selected_asp_id), None)
            if curr_asp:
                st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

                # Calculate direct consultations from this mentee
                all_guide_tickets = list_guide_requests(guide_id) or []
                asp_tickets = [t for t in all_guide_tickets if t.get("aspirant_id") == selected_asp_id]
                open_cnt = sum(1 for t in asp_tickets if t.get("status") in ["OPEN", "IN_PROGRESS", "ACTION_REQUIRED"])

                # 5 Dedicated Context Tabs for Selected Aspirant
                consult_label = "💬 Consultations"
                subtabs = st.tabs([
                    "👤 Profile",
                    "🎬 Journey",
                    "🤝 Guidance Team",
                    "🏦 Scheme Matches",
                    consult_label
                ])

                # ─────────────────────────────────────────────────────────
                # SUBTAB 1: ASPIRANT PROFILE
                # ─────────────────────────────────────────────────────────
                with subtabs[0]:
                    asp_full = get_profile(selected_asp_id) or curr_asp
                    p_data = asp_full.get("profile_data", {})
                    pers = p_data.get("personal", {})
                    prof = p_data.get("professional", {})
                    biz = p_data.get("business", {})
                    demo = p_data.get("demographics", {})

                    st.markdown(f"### Profile Overview: {asp_full.get('full_name')}")

                    # 1. Personal Details
                    st.markdown("#### 1. Personal Details")
                    cp1, cp2, cp3 = st.columns(3)
                    with cp1:
                        st.markdown(f"**Full Name:** {asp_full.get('full_name')}")
                        st.markdown(f"**Email:** {asp_full.get('email')}")
                    with cp2:
                        st.markdown(f"**Phone:** {asp_full.get('phone', 'N/A')}")
                        st.markdown(f"**Gender:** {pers.get('gender', 'N/A')}")
                    with cp3:
                        st.markdown(f"**DOB:** {pers.get('dob', 'N/A')}")
                        st.markdown(f"**Address:** {pers.get('address', 'N/A')}")

                    st.markdown("---")

                    # 2. Professional Background
                    st.markdown("#### 2. Professional Background")
                    cpr1, cpr2 = st.columns(2)
                    with cpr1:
                        st.markdown(f"**Education / Qualification:** {prof.get('education', 'N/A')}")
                        st.markdown(f"**Key Skills:** {prof.get('skills', 'N/A')}")
                    with cpr2:
                        st.markdown(f"**Experience:** {prof.get('experience', 'N/A')}")
                        st.markdown(f"**Certifications / Training:** {prof.get('certifications', 'N/A')}")

                    st.markdown("---")

                    # 3. Business & Venture Details
                    st.markdown("#### 3. Business & Venture Details")
                    cb1, cb2, cb3 = st.columns(3)
                    with cb1:
                        st.markdown(f"**Business Name:** {biz.get('business_name', 'N/A')}")
                        st.markdown(f"**Business Type:** {biz.get('business_type', 'N/A')}")
                    with cb2:
                        st.markdown(f"**Industry Sector:** {biz.get('sector', 'N/A')}")
                        st.markdown(f"**Development Stage:** {biz.get('stage', 'N/A')}")
                    with cb3:
                        st.markdown(f"**Annual Revenue:** {biz.get('revenue', 'N/A')}")
                        st.markdown(f"**Employee Count:** {biz.get('employee_count', 0)}")

                    st.markdown(f"**Description:** {biz.get('description', 'N/A')}")

                    st.markdown("---")

                    # 4. Demographics & Special Eligibility
                    st.markdown("#### 4. Demographics & Eligibility Criteria")
                    cd1, cd2, cd3 = st.columns(3)
                    with cd1:
                        st.markdown(f"**District:** {asp_full.get('district', 'N/A')}")
                        st.markdown(f"**State:** {asp_full.get('state', 'Tamil Nadu')}")
                    with cd2:
                        st.markdown(f"**Founder Category:** {demo.get('founder_category', 'General')}")
                    with cd3:
                        dpiit_tag = "✅ Yes" if demo.get("is_dpiit_recognized") else "❌ No"
                        tn_tag = "✅ Yes" if demo.get("is_startuptn_registered") else "❌ No"
                        women_tag = "✅ Yes" if demo.get("is_women_led") else "❌ No"
                        st.markdown(f"**DPIIT Recognized:** {dpiit_tag}")
                        st.markdown(f"**StartupTN Registered:** {tn_tag}")
                        st.markdown(f"**Women-Led Enterprise:** {women_tag}")

                # ─────────────────────────────────────────────────────────
                # SUBTAB 2: ASPIRANT JOURNEY TIMELINE
                # ─────────────────────────────────────────────────────────
                with subtabs[1]:
                    st.markdown(f"### Mentorship Workspace: {curr_asp['full_name']}")

                    with st.expander(f"➕ Log Mentorship Contribution to {curr_asp['full_name']}'s Journey", expanded=False):
                        with st.form("form_guide_add_entry"):
                            col_g1, col_g2 = st.columns(2)
                            with col_g1:
                                m_title = st.text_input("Title / Milestone", placeholder="e.g. Business Model & PMEGP Review")
                                m_topic_sel = st.selectbox("Topic / Domain", [
                                    "Pricing & Model",
                                    "Market Strategy",
                                    "PMEGP Loan Preparation",
                                    "Customer Discovery",
                                    "Unit Economics",
                                    "Operations",
                                    "Other / Specialized Advisory (Specify)"
                                ])
                                m_topic = m_topic_sel
                                if m_topic_sel == "Other / Specialized Advisory (Specify)":
                                    m_topic_custom = st.text_input("Specify Advisory Topic *", placeholder="e.g. Export Documentation", key="guide_custom_topic")
                                    if m_topic_custom and m_topic_custom.strip():
                                        m_topic = m_topic_custom.strip()
                            with col_g2:
                                m_date = st.date_input("Session Date", value=date.today())
                            m_desc = st.text_area("Guidance Notes / What was achieved?", placeholder="Reviewed DPR proposal, verified eligibility criteria, and recommended applying for subsidy.")

                            if st.form_submit_button("SAVE JOURNEY CONTRIBUTION", type="primary"):
                                if m_title and m_desc:
                                    ev, err = add_guide_contribution(
                                        aspirant_id=selected_asp_id,
                                        guide_id=guide_id,
                                        title=m_title,
                                        description=m_desc,
                                        topic=m_topic,
                                        event_date=m_date.isoformat()
                                    )
                                    if ev:
                                        st.success(f"Added mentorship contribution to {curr_asp['full_name']}'s Journey!")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to add contribution.")
                                else:
                                    st.warning("Please fill in both title and description.")

                    st.markdown(f"#### Complete Journey Narrative Spine")
                    if "del_event_success" in st.session_state:
                        _d_msg = st.session_state.pop("del_event_success")
                        st.success(_d_msg)
                        try:
                            st.toast(_d_msg, icon="✅")
                        except Exception:
                            pass
                    if "del_event_err" in st.session_state:
                        st.error(st.session_state.pop("del_event_err"))

                    timeline = get_journey_timeline(selected_asp_id)
                    if not timeline:
                        st.info("No journey events recorded yet for this founder.")
                    else:
                        for event in timeline:
                            actor_role = event.get("actor_role", "aspirant")
                            actor_name = event.get("actor_name")
                            if actor_role == "system":
                                actor_name = "Platform Intelligence"
                            elif not actor_name:
                                if actor_role == "aspirant":
                                    actor_name = "Entrepreneur"
                                elif actor_role == "guide":
                                    actor_name = "Dedicated Guide"
                                elif actor_role == "sme":
                                    actor_name = "Domain SME"
                                else:
                                    actor_name = "Advisory Council"
                            std_role = get_standard_role_label(actor_role)
                            ev_data = event.get("event_data", {})
                            raw_title = ev_data.get("title") or event.get("event_type") or "Milestone"
                            raw_desc = ev_data.get("description", "")
                            title = html.escape(str(raw_title))
                            desc = html.escape(str(raw_desc)).replace("\n", "<br>")
                            date_display = str(event.get("event_date", ""))[:10]

                            badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                            col_t, col_b, col_act = st.columns([1.2, 5.2, 0.8])
                            with col_t:
                                st.markdown(f"""
                                <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                                <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{std_role}</span>
                                """, unsafe_allow_html=True)
                            with col_b:
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                    <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">{title}</div>
                                    <div style="color:#334155; font-size:0.9rem; margin-top:0.3rem; line-height:1.5;">{desc}</div>
                                    <div style="font-size:0.75rem; color:#64748B; margin-top:0.4rem;">Contributor: <strong>{actor_name}</strong> ({std_role})</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_act:
                                if event.get("actor_id") == guide_id and actor_role == "guide":
                                    if st.button("🗑️", key=f"guide_del_{event['id']}", help="Delete your contribution"):
                                        ok, err = soft_delete_event(event["id"], guide_id, "guide")
                                        if ok:
                                            st.session_state["del_event_success"] = "Mentorship contribution deleted."
                                        else:
                                            st.session_state["del_event_err"] = err or "Could not delete contribution."
                                        st.rerun()

                # ─────────────────────────────────────────────────────────
                # SUBTAB 3: ASSIGNED MENTORS
                # ─────────────────────────────────────────────────────────
                with subtabs[2]:
                    st.markdown(f"### Guidance Team for {curr_asp['full_name']}")
                    st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Institutional mentors and specialized domain experts assigned to collaborate on this entrepreneur's scaling journey.</p>", unsafe_allow_html=True)
                    mentors = get_aspirant_mentors(selected_asp_id)
                    m_guide = mentors.get("guide")
                    m_sme = mentors.get("sme")
                    m_smes = mentors.get("smes", [])
                    if not m_smes and m_sme:
                        m_smes = [m_sme]

                    col_mg1, col_mg2 = st.columns(2)
                    with col_mg1:
                        st.markdown("#### 🧭 Assigned Guide")
                        if m_guide:
                            gp = m_guide.get("profile_data", {})
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:12px; padding:1.2rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                                <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{m_guide.get('full_name')}</div>
                                <div style="color:#059669; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Dedicated Enterprise Mentor · {m_guide.get('district', 'Tamil Nadu')}</div>
                                <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Expertise:</strong> {gp.get('expertise', 'Enterprise Guidance')}</p>
                                <p style="font-size:0.82rem; color:#64748B; margin-top:0.5rem;"><em>"{gp.get('bio', 'Assigned by Administrator')}"</em></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("No Guide assigned.")

                    with col_mg2:
                        smes_count = len(m_smes)
                        header_label = f"🔬 Domain Advisory Panel ({smes_count} Specialists)" if smes_count > 1 else "🔬 Assigned Domain SME"
                        st.markdown(f"#### {header_label}")
                        if m_smes:
                            for idx, sp_item in enumerate(m_smes):
                                sp = sp_item.get("profile_data", {})
                                s_name = sp_item.get("full_name", "Specialist")
                                s_dist = sp_item.get("district", "Tamil Nadu")
                                s_exp = sp.get("expertise") or sp.get("industry") or "Technical & Compliance Advisory"
                                s_ind = sp.get("industry") or "Compliance"
                                s_bio = sp.get("bio") or "Assigned by Administrator to provide specialized domain advisory."
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:12px; padding:1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div style="font-size:1.15rem; font-weight:800; color:#0F172A;">{s_name}</div>
                                        <span style="background:#FFFBEB; color:#D97706; border:1px solid #FDE68A; font-size:0.72rem; font-weight:800; padding:2px 8px; border-radius:6px;">SPECIALIST #{idx+1}</span>
                                    </div>
                                    <div style="color:#D97706; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Subject Matter Expert · {s_dist}</div>
                                    <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Specialization:</strong> {s_exp}</p>
                                    <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Industry:</strong> {s_ind}</p>
                                    <p style="font-size:0.82rem; color:#64748B; margin-top:0.5rem;"><em>"{s_bio}"</em></p>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No Domain SME assigned yet. The Admin assigns specialized experts when required.")

                # ─────────────────────────────────────────────────────────
                # SUBTAB 4: SCHEME MATCHES (THE GATEKEEPER WORKSPACE)
                # ─────────────────────────────────────────────────────────
                with subtabs[3]:
                    st.markdown("### 🏦 Scheme Gatekeeper Workspace")
                    st.markdown(f"<p style='color:#64748B; font-size:0.9rem;'>AI-suggested matches and full catalogue access for <strong>{curr_asp['full_name']}</strong>. Evaluate, review insider intelligence & red flags, and release curated opportunities.</p>", unsafe_allow_html=True)

                    if f"guide_release_success_{selected_asp_id}" in st.session_state:
                        succ_msg = st.session_state.pop(f"guide_release_success_{selected_asp_id}")
                        st.success(succ_msg)
                        try:
                            st.toast(succ_msg, icon="🚀")
                        except Exception:
                            pass

                    # ═══════════════════════════════════════════════════════
                    # SECTION A: 🎯 AI-SUGGESTED MATCHES
                    # ═══════════════════════════════════════════════════════
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg, #11131F 0%, #1E1B4B 100%); border:1.5px solid #8B5CF6; border-radius:14px; padding:1.2rem 1.5rem; margin-bottom:1.2rem; box-shadow:0 4px 20px rgba(139,92,246,0.15);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="font-size:1.15rem; font-weight:800; color:#FFFFFF;">🎯 AI-Suggested Scheme Matches</div>
                                <div style="font-size:0.85rem; color:#A5B4FC; margin-top:2px;">Algorithmically matched against {_safe_esc(curr_asp.get('full_name', 'Entrepreneur'))}'s venture profile, sector, stage & demographics</div>
                            </div>
                            <span style="font-size:0.8rem; font-weight:700; background:rgba(139,92,246,0.3); color:#C4B5FD; padding:4px 12px; border-radius:8px;">Deterministic Engine</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Run matching engine (instant in-memory matching with pre-loaded profile)
                    suggested_matches = match_schemes_for_aspirant(selected_asp_id, profile=curr_asp)

                    if not suggested_matches:
                        st.info(f"No schemes scored ≥60% match for {curr_asp['full_name']}'s current profile. Try updating the Aspirant's profile data or browse the full catalogue below.")
                    else:
                        # Show summary metrics
                        top_score = suggested_matches[0]["match_score"] if suggested_matches else 0
                        high_matches = len([m for m in suggested_matches if m["match_score"] >= 80])
                        st.markdown(f"""
                        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:1rem;">
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.85rem 1rem; text-align:center;">
                                <div style="font-size:2rem; font-weight:800; color:#8B5CF6;">{len(suggested_matches)}</div>
                                <div style="font-size:0.8rem; color:#64748B; font-weight:600;">Matched Schemes (≥60%)</div>
                            </div>
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.85rem 1rem; text-align:center;">
                                <div style="font-size:2rem; font-weight:800; color:#10b981;">{high_matches}</div>
                                <div style="font-size:0.8rem; color:#64748B; font-weight:600;">Recommended (≥80%)</div>
                            </div>
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:0.85rem 1rem; text-align:center;">
                                <div style="font-size:2rem; font-weight:800; color:#F59E0B;">{top_score}%</div>
                                <div style="font-size:0.8rem; color:#64748B; font-weight:600;">Top Match Score</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Display top 10, rest in expander
                        top_matches = suggested_matches[:10]
                        remaining_matches = suggested_matches[10:]

                        def _render_suggested_card(match, card_idx):
                            """Render a single AI-suggested match as an expandable card."""
                            m_score = match["match_score"]
                            m_status = match["recommendation_status"]
                            score_bg = "#10b981" if m_score >= 80 else "#F59E0B"
                            m_scheme = match.get("scheme", match)
                            m_name = _safe_esc(match.get("name"), default="Scheme")
                            m_agency = _safe_esc(match.get("agency"), default="")
                            m_amount = _safe_esc(match.get("amount"), default="")
                            m_ftype = _safe_esc(match.get("funding_type"), default="Grant")
                            m_id = match["id"]

                            with st.expander(f"{m_score}% — {match.get('name', 'Scheme')} ({m_agency}) · {m_ftype} | {match.get('amount', '')}", expanded=False):
                                # Score banner
                                st.markdown(f"""
                                <div style="background:#11131F; border:1.5px solid #8B5CF6; border-radius:12px; padding:1rem; margin-bottom:0.75rem; box-shadow:0 4px 20px rgba(139,92,246,0.12);">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div>
                                            <div style="font-size:1.1rem; font-weight:800; color:#FFFFFF;">{m_name}</div>
                                            <div style="font-size:0.82rem; color:#94A3B8; margin-top:2px;">
                                                {m_agency} · <span style="color:#C4B5FD; font-weight:700;">{m_ftype}</span> · <span style="color:#34D399; font-weight:700;">{m_amount}</span>
                                            </div>
                                        </div>
                                        <span style="background:{score_bg}; color:#ffffff; font-weight:800; font-size:0.9rem; padding:4px 14px; border-radius:12px;">{m_score}% ({m_status})</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Match reasons
                                reasons = match.get("match_reasons", [])
                                reasons_html = "".join([f"<li style='margin-bottom:3px;'><strong style='color:#10b981;'>✓</strong> {_safe_esc(r)}</li>" for r in reasons])
                                concerns = match.get("potential_concerns", [])
                                concerns_html = "".join([f"<li style='margin-bottom:3px;'><strong style='color:#F59E0B;'>⚠</strong> {_safe_esc(c)}</li>" for c in concerns]) if concerns else ""

                                st.markdown(f"""
                                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.5rem;">
                                    <strong style="color:#166534; font-size:0.88rem;">Match Reasoning:</strong>
                                    <ul style="font-size:0.83rem; color:#14532D; margin:0.3rem 0 0 1rem; padding:0;">{reasons_html}</ul>
                                </div>
                                """, unsafe_allow_html=True)

                                if concerns_html:
                                    st.markdown(f"""
                                    <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.5rem;">
                                        <strong style="color:#92400E; font-size:0.88rem;">Potential Concerns:</strong>
                                        <ul style="font-size:0.83rem; color:#78350F; margin:0.3rem 0 0 1rem; padding:0;">{concerns_html}</ul>
                                    </div>
                                    """, unsafe_allow_html=True)

                                # Guide-Only Private Intelligence
                                agenda_str = parse_list_field(
                                    m_scheme.get("hidden_agenda"),
                                    default=">> Emphasize local job creation, import substitution & revenue growth."
                                )
                                flags_str = parse_list_field(
                                    m_scheme.get("red_flags"),
                                    default="!! Verify official sanction terms, audit rules & equity rights before signing."
                                )

                                st.markdown(f"""
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:0.85rem;">
                                    <div style="background:#FFFDF0; border:1.5px solid #F59E0B; border-left:5px solid #D97706; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#0F172A; line-height:1.55; box-shadow:0 1px 3px rgba(217,119,6,0.08);">
                                        <div style="font-weight:900; color:#92400E; margin-bottom:6px; font-size:0.84rem; letter-spacing:0.4px; text-transform:uppercase;">🤫 INSIDER INTELLIGENCE (Guide Only):</div>
                                        <div style="color:#0F172A; font-weight:600;">{agenda_str}</div>
                                    </div>
                                    <div style="background:#FFF5F5; border:1.5px solid #F87171; border-left:5px solid #DC2626; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#0F172A; line-height:1.55; box-shadow:0 1px 3px rgba(220,38,38,0.08);">
                                        <div style="font-weight:900; color:#991B1B; margin-bottom:6px; font-size:0.84rem; letter-spacing:0.4px; text-transform:uppercase;">⚠️ RED FLAGS (Guide Only):</div>
                                        <div style="color:#0F172A; font-weight:600;">{flags_str}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Release Form
                                with st.form(f"form_sug_release_{selected_asp_id}_{m_id}_{card_idx}"):
                                    st.markdown("##### 🎯 Release This Scheme to Aspirant")
                                    sg_rec = st.text_area(
                                        "Recommendation Note * (Visible to founder)",
                                        placeholder=f"e.g. Your venture qualifies for {match.get('amount', 'this funding')} under {match.get('name')}. Prepare your DPR before applying.",
                                        height=80,
                                        key=f"sug_rec_{m_id}_{card_idx}"
                                    )
                                    sg_note = st.text_input(
                                        "Internal Guide Note (Hidden from founder)",
                                        placeholder="e.g. Follow up on bank branch manager contact.",
                                        key=f"sug_note_{m_id}_{card_idx}"
                                    )
                                    if st.form_submit_button("🚀 RELEASE TO ASPIRANT", type="primary", use_container_width=True):
                                        if not sg_rec.strip():
                                            st.warning("Please provide a recommendation note.")
                                        else:
                                            ok, msg = release_scheme_to_aspirant(
                                                guide_id=guide_id,
                                                aspirant_id=selected_asp_id,
                                                scheme_id=m_id,
                                                guide_recommendation=sg_rec.strip(),
                                                guide_note=sg_note.strip()
                                            )
                                            if ok:
                                                st.session_state[f"guide_release_success_{selected_asp_id}"] = f"🚀 Successfully released '{match.get('name')}' to {curr_asp['full_name']}! The scheme is now visible in their funding portal."
                                                st.rerun()
                                            else:
                                                st.error(msg or "Failed to release scheme.")

                        # Render top 10
                        for idx, m in enumerate(top_matches):
                            _render_suggested_card(m, idx)

                        # Remaining matches in expander
                        if remaining_matches:
                            with st.expander(f"📊 View {len(remaining_matches)} More Matches (60-{remaining_matches[0]['match_score']}%)", expanded=False):
                                for idx, m in enumerate(remaining_matches):
                                    _render_suggested_card(m, idx + 10)

                    # ═══════════════════════════════════════════════════════
                    # SECTION B: 📋 BROWSE FULL CATALOGUE
                    # ═══════════════════════════════════════════════════════
                    st.markdown("---")
                    with st.expander("📋 Browse Full Master Catalogue (Manual Search & Evaluate)", expanded=False):
                        st.markdown(f"<p style='color:#64748B; font-size:0.85rem;'>Manually search the entire 170+ scheme catalogue. Useful for finding schemes the algorithm may have scored below 60% threshold.</p>", unsafe_allow_html=True)

                        c_s1, c_s2, c_s3 = st.columns([2.5, 1.2, 1.2])
                        with c_s1:
                            g_sc_search = st.text_input("🔍 Search Master Catalogue", placeholder="e.g. PMEGP, TANSEED, NEEDS, MUDRA...", key="g_sc_search")
                        with c_s2:
                            g_sc_cat = st.selectbox("Category", ["ALL"] + MASTER_CATEGORY_TYPES, key="g_sc_cat")
                        with c_s3:
                            g_sc_stage = st.selectbox("Stage", ["ALL"] + MASTER_STAGES, key="g_sc_stage")

                        available_schemes = list_schemes(search=g_sc_search, category=g_sc_cat, stage=g_sc_stage, active_only=True)

                        if not available_schemes:
                            st.info("No matching schemes found in master catalogue.")
                        else:
                            scheme_dict = {
                                s["id"]: f"{s['name']} ({s.get('agency','Govt')}) — {s.get('funding_type','Grant')} | {s.get('amount','')}"
                                for s in available_schemes
                            }
                            eval_scheme_id = st.selectbox(
                                "Select Scheme to Evaluate",
                                list(scheme_dict.keys()),
                                format_func=lambda x: scheme_dict[x],
                                key="g_eval_scheme_select"
                            )

                            col_btn1, col_btn2 = st.columns([2, 3])
                            with col_btn1:
                                gen_clicked = st.button("⚡ GENERATE SCHEME EVALUATION", type="primary", use_container_width=True, key=f"btn_gen_eval_{eval_scheme_id}")

                            eval_state_key = f"active_eval_{selected_asp_id}_{eval_scheme_id}"
                            if gen_clicked or st.session_state.get(eval_state_key):
                                st.session_state[eval_state_key] = True
                                evaluation = evaluate_scheme_for_aspirant(selected_asp_id, eval_scheme_id)
                                eval_scheme = evaluation["scheme"]

                                score = evaluation["match_score"]
                                status_label = evaluation["recommendation_status"]
                                score_color = "#10b981" if score >= 80 else "#f59e0b"

                                st.markdown(f"""
                                <div style="background:#11131F; border:1.5px solid #8B5CF6; border-radius:12px; padding:1.2rem; margin:1rem 0; box-shadow:0 4px 20px rgba(139,92,246,0.12);">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div>
                                            <div style="font-size:1.2rem; font-weight:800; color:#FFFFFF;">{_safe_esc(eval_scheme.get('name'), default='Untitled Scheme')}</div>
                                            <div style="font-size:0.85rem; color:#94A3B8; margin-top:2px;">
                                                {_safe_esc(eval_scheme.get('agency'), default='')} · <span style="color:#C4B5FD; font-weight:700;">{_safe_esc(eval_scheme.get('funding_type'), default='Grant')}</span> · <span style="color:#34D399; font-weight:700;">{_safe_esc(eval_scheme.get('amount'), default='')}</span>
                                            </div>
                                        </div>
                                        <span style="background:{score_color}; color:#ffffff; font-weight:800; font-size:0.95rem; padding:4px 14px; border-radius:12px;">{score}% Match ({status_label})</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Match Reasons checklist & Eligibility
                                reasons = evaluation.get("match_reasons", [])
                                reasons_html = "".join([f"<li style='margin-bottom:3px;'><strong style='color:#10b981;'>✓</strong> {_safe_esc(r)}</li>" for r in reasons])
                                st.markdown(f"""
                                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.75rem;">
                                    <strong style="color:#166534; font-size:0.9rem;">Match Reasoning & Profile Alignment:</strong>
                                    <ul style="font-size:0.85rem; color:#14532D; margin:0.4rem 0 0 1rem; padding:0;">{reasons_html}</ul>
                                </div>
                                """, unsafe_allow_html=True)

                                # Guide-Only Private Intelligence
                                agenda_str = parse_list_field(
                                    eval_scheme.get("hidden_agenda"),
                                    default=">> Emphasize local job creation, import substitution & revenue growth."
                                )
                                flags_str = parse_list_field(
                                    eval_scheme.get("red_flags"),
                                    default="!! Verify official sanction terms, audit rules & equity rights before signing."
                                )

                                st.markdown(f"""
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:1rem;">
                                    <div style="background:#FFFDF0; border:1.5px solid #F59E0B; border-left:5px solid #D97706; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#0F172A; line-height:1.55; box-shadow:0 1px 3px rgba(217,119,6,0.08);">
                                        <div style="font-weight:900; color:#92400E; margin-bottom:6px; font-size:0.85rem; letter-spacing:0.4px; text-transform:uppercase;">🤫 INSIDER INTELLIGENCE / HIDDEN AGENDA (Guide Only):</div>
                                        <div style="color:#0F172A; font-weight:600;">{agenda_str}</div>
                                    </div>
                                    <div style="background:#FFF5F5; border:1.5px solid #F87171; border-left:5px solid #DC2626; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#0F172A; line-height:1.55; box-shadow:0 1px 3px rgba(220,38,38,0.08);">
                                        <div style="font-weight:900; color:#991B1B; margin-bottom:6px; font-size:0.85rem; letter-spacing:0.4px; text-transform:uppercase;">⚠️ RED FLAGS / STRICT CAUTIONS (Guide Only):</div>
                                        <div style="color:#0F172A; font-weight:600;">{flags_str}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Release Action Form
                                with st.form(f"form_release_{selected_asp_id}_{eval_scheme_id}"):
                                    st.markdown("#### 🎯 Release Scheme to Aspirant")
                                    g_rec_input = st.text_area(
                                        "Guide Recommendation Note for Aspirant * (Visible to the founder)",
                                        placeholder=f"e.g. Recommended because your venture qualifies for 35% capital subsidy under {eval_scheme.get('name')}. Ensure your project DPR is completed before applying.",
                                        height=90
                                    )
                                    g_note_input = st.text_input(
                                        "Internal Guide Note (Private record for Guide and Admin, hidden from founder)",
                                        placeholder="e.g. Founder needs follow-up session on bank branch manager contact."
                                    )

                                    rel_submit = st.form_submit_button("🚀 RELEASE TO ASPIRANT", type="primary", use_container_width=True)
                                    if rel_submit:
                                        if not g_rec_input.strip():
                                            st.warning("Please provide a recommendation note explaining why you recommend this scheme.")
                                        else:
                                            ok, msg = release_scheme_to_aspirant(
                                                guide_id=guide_id,
                                                aspirant_id=selected_asp_id,
                                                scheme_id=eval_scheme_id,
                                                guide_recommendation=g_rec_input.strip(),
                                                guide_note=g_note_input.strip()
                                            )
                                            if ok:
                                                st.session_state[f"guide_release_success_{selected_asp_id}"] = f"🚀 Successfully released '{eval_scheme.get('name')}' to {curr_asp['full_name']}! The scheme is now visible in their funding portal."
                                                st.rerun()
                                            else:
                                                st.error(msg or "Failed to release scheme.")

                    # ─────────────────────────────────────────────────────
                    # RELEASE HISTORY & MANAGEMENT SECTION
                    # ─────────────────────────────────────────────────────
                    st.markdown("---")
                    st.subheader(f"Release History for {curr_asp['full_name']}")
                    releases = get_guide_scheme_releases(guide_id, selected_asp_id)
                    active_releases = [r for r in releases if r.get("status") == "RELEASED"]
                    withdrawn_releases = [r for r in releases if r.get("status") == "WITHDRAWN"]

                    st.markdown(f"##### Active Releases ({len(active_releases)})")
                    if not active_releases:
                        st.info(f"No schemes are currently active for {curr_asp['full_name']}.")
                    else:
                        for rel in active_releases:
                            c_r1, c_r2 = st.columns([3.5, 1.2])
                            with c_r1:
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #8B5CF6; border-radius:0 10px 10px 0; padding:1rem; margin-bottom:0.6rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                    <div style="font-weight:800; font-size:1.05rem; color:#0F172A;">{_safe_esc(rel.get('scheme_name'), default='Scheme')}</div>
                                    <div style="font-size:0.84rem; color:#64748B; margin:2px 0 6px 0;">
                                        {_safe_esc(rel.get('scheme_agency'), default='')} · Released: {str(rel.get('released_at',''))[:10]}
                                    </div>
                                    <div style="font-size:0.86rem; color:#334155; background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0;">
                                        <strong style="color:#7C3AED;">Recommendation Note:</strong> {_safe_esc(rel.get('guide_recommendation'), default='No note provided')}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            with c_r2:
                                st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
                                if st.button("📦 Withdraw Release", key=f"btn_withd_{rel.get('scheme_id')}_{rel.get('id')}", use_container_width=True):
                                    ok, err = withdraw_scheme_release(guide_id, selected_asp_id, rel.get("scheme_id"))
                                    if ok:
                                        st.success(f"Withdrew release for '{rel.get('scheme_name')}'.")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to withdraw release.")

                    if withdrawn_releases:
                        with st.expander(f"📦 Withdrawn Releases ({len(withdrawn_releases)})", expanded=False):
                            for w in withdrawn_releases:
                                st.markdown(f"""
                                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #94A3B8; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-bottom:0.5rem;">
                                    <div style="font-weight:700; color:#475569;">{_safe_esc(w.get('scheme_name'), default='Scheme')}</div>
                                    <div style="font-size:0.8rem; color:#94A3B8;">Withdrawn: {str(w.get('withdrawn_at',''))[:16]}</div>
                                </div>
                                """, unsafe_allow_html=True)

                # ─────────────────────────────────────────────────────────
                # SUBTAB 5: ASPIRANT CONSULTATIONS & DIRECT QUERIES
                # ─────────────────────────────────────────────────────────
                with subtabs[4]:
                    open_pill = f' <span style="background:#FEF3C7; color:#B45309; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:6px; vertical-align:middle;">{open_cnt} Open</span>' if open_cnt > 0 else ""
                    st.markdown(f"### Direct Consultations: {curr_asp['full_name']}{open_pill}", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#64748B; font-size:0.9rem;'>Consultation requests and proactive guidance directives with <strong>{curr_asp['full_name']}</strong>.</p>", unsafe_allow_html=True)

                    with st.expander(f"➕ Issue Guidance Directive / Check-in to {curr_asp['full_name']}", expanded=False):
                        with st.form(f"form_guide_init_consult_{selected_asp_id}"):
                            c_gc1, c_gc2 = st.columns([2, 1])
                            with c_gc1:
                                gc_subj = st.text_input("Subject / Action Item *", placeholder="e.g. Upload Competitive Machinery Quotations for PMEGP DPR", key=f"gc_subj_{selected_asp_id}")
                            with c_gc2:
                                gc_cat_options = {
                                    "BANKING_DPR": "Banking, DPR & Financials",
                                    "SCHEMES_SUBSIDIES": "Scheme Eligibility & Subsidies",
                                    "GENERAL": "General Mentorship & Strategy",
                                    "SCALING_OPERATIONS": "Venture Scaling & Operations",
                                    "OTHERS": "Other Specific Guidance"
                                }
                                gc_cat = st.selectbox("Category", list(gc_cat_options.keys()), format_func=lambda k: gc_cat_options[k], key=f"gc_cat_{selected_asp_id}")

                            gc_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1, key=f"gc_prio_{selected_asp_id}")
                            gc_msg = st.text_area("Guidance Directive / Action Required *", placeholder=f"Specify what {curr_asp['full_name']} needs to do or provide...", height=90, key=f"gc_msg_{selected_asp_id}")

                            if st.form_submit_button("🚀 SEND GUIDANCE DIRECTIVE TO ASPIRANT", type="primary"):
                                if not gc_subj.strip():
                                    st.warning("Please provide a subject for this guidance directive.")
                                elif not gc_msg.strip():
                                    st.warning("Please provide the guidance instructions / action required.")
                                else:
                                    req, err = create_mentor_consultation(
                                        mentor_id=guide_id,
                                        mentor_role="guide",
                                        aspirant_id=selected_asp_id,
                                        subject=gc_subj.strip(),
                                        message=gc_msg.strip(),
                                        priority=gc_prio,
                                        category=gc_cat
                                    )
                                    if req:
                                        st.success(f"Guidance directive dispatched to {curr_asp['full_name']}!")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to dispatch directive.")

                    if not asp_tickets:
                        st.info(f"No consultations currently recorded with {curr_asp['full_name']}. You may initiate a guidance directive above.")
                    else:
                        for t in asp_tickets:
                            t_status = t.get("status", "OPEN")
                            st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status in ["IN_PROGRESS", "REPLIED"] else "#10b981"
                            is_mentor_init = (t.get("request_type") == "mentor_initiated" or t.get("requester_role") == "guide")

                            escaped_subject = _safe_esc(t.get('subject', 'Support Ticket'))
                            escaped_asp_name = _safe_esc(t.get('aspirant_name') or curr_asp.get('full_name', 'Entrepreneur'))
                            escaped_asp_email = _safe_esc(t.get('aspirant_email') or curr_asp.get('email', ''))
                            escaped_message = _safe_esc(t.get('message', '')).replace('\n', '<br>')

                            if is_mentor_init:
                                origin_badge = '<span style="font-size:0.75rem; font-weight:800; background:#059669; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:6px;">🧭 INITIATED BY YOU</span>'
                                from_line = f'Directive issued by you to: <strong style="color:#0F172A;">{escaped_asp_name}</strong>'
                            else:
                                origin_badge = '<span style="font-size:0.75rem; font-weight:800; background:#3B82F6; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:6px;">🌱 FROM FOUNDER</span>'
                                from_line = f'From: <strong style="color:#0F172A;">{escaped_asp_name}</strong> ({escaped_asp_email})'

                            guide_resp_html = ""
                            if t.get('guide_response'):
                                g_resp = _safe_esc(t.get('guide_response') or '').replace('\n', '<br>')
                                guide_resp_html = f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:3px solid #10b981; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#166534; margin-top:0.5rem;"><strong>Your Guidance Response:</strong> {g_resp}</div>'

                            asp_resp_html = ""
                            asp_reply = t.get('aspirant_response') or (t.get('admin_response', '').replace('Aspirant Reply: ', '') if str(t.get('admin_response', '')).startswith('Aspirant Reply: ') else '')
                            if asp_reply:
                                a_resp = _safe_esc(asp_reply).replace('\n', '<br>')
                                asp_resp_html = f'<div style="background:#EFF6FF; border:1px solid #BFDBFE; border-left:3px solid #3B82F6; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#1E40AF; margin-top:0.5rem;"><strong>🌱 Founder Response / Updates:</strong> {a_resp}</div>'

                            card_html = (
                                f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {st_color}; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                                f'<div><span style="font-size:1.1rem; font-weight:800; color:#0F172A;">{escaped_subject}</span>'
                                f'<span style="font-size:0.75rem; font-weight:800; background:{st_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:8px;">{t_status}</span>'
                                f'<span style="font-size:0.75rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("priority","MEDIUM")}</span>'
                                f'{origin_badge}</div>'
                                f'<div style="font-size:0.8rem; color:#64748B;">{str(t.get("created_at",""))[:16]}</div>'
                                f'</div>'
                                f'<div style="font-size:0.85rem; color:#64748B; margin:4px 0;">{from_line}</div>'
                                f'<div style="font-size:0.9rem; color:#334155; margin-top:0.4rem; line-height:1.45;">{escaped_message}</div>'
                                f'{guide_resp_html}'
                                f'{asp_resp_html}'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                            if t_status in ["OPEN", "IN_PROGRESS", "REPLIED"]:
                                with st.expander(f"💬 Provide Advisory Guidance / Update Status for '{t.get('subject')}'", expanded=False):
                                    with st.form(f"form_guide_resp_sub_{t['id']}"):
                                        c_r1, c_r2 = st.columns([1, 2])
                                        with c_r1:
                                            new_st = st.selectbox("Update Status", ["IN_PROGRESS", "RESOLVED"], key=f"sel_st_sub_{t['id']}")
                                        with c_r2:
                                            resp_text = st.text_area("Guidance / Recommendation *", placeholder="Enter specific instructions or confirm resolution...", height=80, key=f"txt_resp_sub_{t['id']}")

                                        if st.form_submit_button("Submit Guidance & Update", type="primary"):
                                            if not resp_text.strip():
                                                st.warning("Please enter your guidance response.")
                                            else:
                                                ok, err = guide_respond_request(t["id"], guide_id, new_st, resp_text.strip())
                                                if ok:
                                                    st.success("Guidance response recorded and student notified!")
                                                    st.rerun()
                                                else:
                                                    st.error(err or "Failed to record response.")

                    # ── INSTITUTIONAL ROADBLOCKS & ADMIN DIRECTIVES ──
                    st.markdown("---")
                    st.subheader("🏛️ Institutional Roadblocks & Directorate Directives")
                    st.markdown(f"<p style='color:#64748B; font-size:0.9rem;'>Facing policy hurdles, district clearance delays, or requiring co-mentor intervention for <strong>{curr_asp['full_name']}</strong>? Request an official administrative directive from the Program Directorate. <em>(Strictly invisible to the entrepreneur)</em></p>", unsafe_allow_html=True)

                    admin_queries = list_mentor_admin_queries(mentor_id=guide_id, aspirant_id=selected_asp_id)
                    if admin_queries:
                        st.markdown("##### 📜 Directorate Inquiries & Issued Directives")
                        for q in admin_queries:
                            q_st = q.get("status", "PENDING_ADMIN")
                            q_color = "#f59e0b" if q_st == "PENDING_ADMIN" else "#10b981"
                            q_sub = _safe_esc(q.get("subject"), default="Institutional Query")
                            q_msg = _safe_esc(q.get("message"), default="").replace("\n", "<br>")

                            directive_html = ""
                            if q.get("admin_directive"):
                                ad_text = _safe_esc(q.get("admin_directive"), default="").replace("\n", "<br>")
                                dir_time = str(q.get("directive_issued_at", ""))[:16]
                                directive_html = (
                                    f'<div style="background:#F0FDF4; border:1px solid #86EFAC; border-left:4px solid #16A34A; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-top:0.6rem;">'
                                    f'<div style="font-weight:800; color:#15803D; font-size:0.88rem; display:flex; justify-content:space-between;">'
                                    f'<span>🏛️ Official Directorate Directive</span>'
                                    f'<span style="font-size:0.75rem; color:#166534; font-weight:600;">Issued: {dir_time}</span>'
                                    f'</div>'
                                    f'<div style="font-size:0.9rem; color:#14532D; margin-top:0.35rem; line-height:1.5;">{ad_text}</div>'
                                    f'</div>'
                                )

                            card_html = (
                                f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {q_color}; border-radius:0 10px 10px 0; padding:1rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
                                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                                f'<div>'
                                f'<span style="font-weight:700; color:#0F172A; font-size:1rem;">{q_sub}</span>'
                                f'<span style="font-size:0.72rem; font-weight:800; background:{q_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:6px;">{q_st}</span>'
                                f'<span style="font-size:0.72rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">Priority: {q.get("priority","MEDIUM")}</span>'
                                f'</div>'
                                f'<div style="font-size:0.78rem; color:#64748B;">{str(q.get("created_at",""))[:16]}</div>'
                                f'</div>'
                                f'<div style="font-size:0.88rem; color:#334155; margin-top:0.4rem; line-height:1.45;">{q_msg}</div>'
                                f'{directive_html}'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                    with st.expander(f"➕ Request Institutional Support / Admin Directive for {curr_asp['full_name']}", expanded=False):
                        with st.form(f"form_guide_admin_query_{selected_asp_id}"):
                            c_aq1, c_aq2 = st.columns([3, 1])
                            with c_aq1:
                                q_subject = st.text_input("Institutional Subject / Blockage *", placeholder="e.g. DIC capital subsidy disbursement delay or Need Co-Guide for export compliance", key=f"gaq_sub_{selected_asp_id}")
                            with c_aq2:
                                q_priority = st.selectbox("Urgency / Priority", ["MEDIUM", "HIGH", "URGENT"], index=0, key=f"gaq_pri_{selected_asp_id}")

                            q_desc = st.text_area("Detailed Roadblock Context & Required Administrative Intervention *", placeholder="Describe the policy hurdle, institutional blockage, or specify if co-guidance / additional domain advisory is needed...", height=90, key=f"gaq_desc_{selected_asp_id}")

                            if st.form_submit_button("Submit Request to Directorate", type="primary"):
                                if not q_subject.strip() or not q_desc.strip():
                                    st.warning("Please provide both a subject and roadblock details.")
                                else:
                                    q_res, q_err = create_mentor_admin_query(
                                        mentor_id=guide_id,
                                        mentor_role="guide",
                                        aspirant_id=selected_asp_id,
                                        subject=q_subject.strip(),
                                        message=q_desc.strip(),
                                        priority=q_priority
                                    )
                                    if q_res:
                                        st.success("Administrative request submitted to Program Directorate! Admin will issue official directives.")
                                        st.rerun()
                                    else:
                                        st.error(q_err or "Failed to submit request.")

    # ─────────────────────────────────────────────────────────────
    # TAB 2: GUIDE CONSULTATIONS QUEUE
    # ─────────────────────────────────────────────────────────────
    with main_tabs[1]:
        st.subheader("Assigned Mentee Consultations")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Consultation requests submitted by your assigned entrepreneurs requiring your mentorship and guidance.</p>", unsafe_allow_html=True)

        col_f1, col_f2 = st.columns([3, 1])
        with col_f2:
            status_filter = st.selectbox("Status Filter", ["ALL", "OPEN", "IN_PROGRESS", "RESOLVED"], key="guide_hr_status_filter")

        guide_tickets = list_guide_requests(guide_id)
        # Only show tickets from currently assigned caseload entrepreneurs
        assigned_asp_ids = {a["id"] for a in (assigned_aspirants or [])}
        guide_tickets = [t for t in (guide_tickets or []) if t.get("aspirant_id") in assigned_asp_ids]

        if status_filter != "ALL":
            guide_tickets = [t for t in guide_tickets if t.get("status") == status_filter]

        if not guide_tickets:
            st.info("No help requests found in this queue.")
        else:
            for t in guide_tickets:
                t_status = t.get("status", "OPEN")
                st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status == "IN_PROGRESS" else "#10b981"

                escaped_subject = _safe_esc(t.get('subject', 'Support Ticket'))
                escaped_asp_name = _safe_esc(t.get('aspirant_name') or 'Entrepreneur')
                escaped_asp_email = _safe_esc(t.get('aspirant_email') or '')
                escaped_message = _safe_esc(t.get('message', '')).replace('\n', '<br>')

                guide_resp_html = ""
                if t.get('guide_response'):
                    g_resp = _safe_esc(t.get('guide_response') or '').replace('\n', '<br>')
                    guide_resp_html = f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:3px solid #10b981; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#166534; margin-top:0.5rem;"><strong>Guide Response:</strong> {g_resp}</div>'

                card_html = (
                    f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {st_color}; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<div><span style="font-size:1.1rem; font-weight:800; color:#0F172A;">{escaped_subject}</span>'
                    f'<span style="font-size:0.75rem; font-weight:800; background:{st_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:8px;">{t_status}</span>'
                    f'<span style="font-size:0.75rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("priority","MEDIUM")}</span></div>'
                    f'<div style="font-size:0.8rem; color:#64748B;">{str(t.get("created_at",""))[:16]}</div>'
                    f'</div>'
                    f'<div style="font-size:0.85rem; color:#64748B; margin:4px 0;">From: <strong style="color:#0F172A;">{escaped_asp_name}</strong> ({escaped_asp_email})</div>'
                    f'<div style="font-size:0.9rem; color:#334155; margin-top:0.4rem; line-height:1.45;">{escaped_message}</div>'
                    f'{guide_resp_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                col_btn_m, _ = st.columns([1, 3])
                with col_btn_m:
                    if st.button("Open Mentee Profile →", key=f"btn_open_mentee_{t['id']}_{t.get('aspirant_id')}"):
                        st.session_state["guide_selected_aspirant"] = t.get("aspirant_id")
                        st.rerun()

                if t_status in ["OPEN", "IN_PROGRESS"]:
                    with st.expander(f"💬 Respond to '{t.get('subject')}'", expanded=False):
                        with st.form(f"form_guide_resp_{t['id']}"):
                            c_rs1, c_rs2 = st.columns([1, 2])
                            with c_rs1:
                                new_st = st.selectbox("Update Status", ["IN_PROGRESS", "RESOLVED"], key=f"sel_st_{t['id']}")
                            with c_rs2:
                                resp_text = st.text_area("Response Message *", placeholder="Provide guidance, action points, or confirm resolution...", height=80, key=f"txt_resp_{t['id']}")

                            if st.form_submit_button("Send Response & Update Ticket", type="primary"):
                                if not resp_text.strip():
                                    st.warning("Please enter a response message.")
                                else:
                                    ok, err = guide_respond_request(t["id"], guide_id, new_st, resp_text.strip())
                                    if ok:
                                        st.success("Response recorded successfully!")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to record response.")

    # ─────────────────────────────────────────────────────────────
    # TAB 3: GUIDE PROFILE & TRANSITION HISTORY
    # ─────────────────────────────────────────────────────────────
    with main_tabs[2]:
        st.subheader("👤 My Guide Profile")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Manage your contact information, advisory credentials, and view your mentorship assignment transitions.</p>", unsafe_allow_html=True)

        cur_profile = get_profile(guide_id) or user_profile
        cur_data = cur_profile.get("profile_data", {})
        if isinstance(cur_data, str):
            import json
            try:
                cur_data = json.loads(cur_data)
            except Exception:
                cur_data = {}

        # Profile Card
        bio_text = _safe_esc(cur_data.get("bio"))
        bio_html = f'<div style="font-size:0.85rem; color:#64748B; margin-top:0.4rem; font-style:italic;">"{bio_text}"</div>' if bio_text else ''
        p_name = _safe_esc(cur_profile.get('full_name') or 'Guide')
        p_dist = _safe_esc(cur_profile.get('district') or 'Tamil Nadu')
        p_email = _safe_esc(cur_profile.get('email') or '')
        p_phone = _safe_esc(cur_profile.get('phone') or 'Not Set')
        p_exp = _safe_esc(cur_data.get('expertise') or 'Business Guidance & Planning')

        card_html = (
            f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:0 12px 12px 0; padding:1.25rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
            f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
            f'<div>'
            f'<h3 style="margin:0; color:#0F172A; font-size:1.35rem;">{p_name}</h3>'
            f'<div style="color:#059669; font-weight:700; font-size:0.9rem; margin-top:2px;">Institutional Enterprise Mentor · {p_dist}</div>'
            f'<div style="color:#475569; font-size:0.85rem; margin-top:0.35rem;">'
            f'<strong>Email:</strong> {p_email} | <strong>Phone:</strong> {p_phone}'
            f'</div>'
            f'<div style="color:#334155; font-size:0.88rem; margin-top:0.4rem;">'
            f'<strong>Primary Expertise:</strong> {p_exp}'
            f'</div>'
            f'{bio_html}'
            f'</div>'
            f'<span style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; font-size:0.75rem; font-weight:800; padding:3px 10px; border-radius:8px;">VERIFIED GUIDE</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander("✏️ Edit My Profile & Contact Information", expanded=False):
            with st.form("form_edit_guide_profile"):
                col_ep1, col_ep2 = st.columns(2)
                with col_ep1:
                    eg_name = st.text_input("Full Name *", value=cur_profile.get("full_name", ""))
                    eg_phone = st.text_input("Phone Number *", value=cur_profile.get("phone", ""), placeholder="e.g. 9876543210")
                with col_ep2:
                    cur_loc = cur_profile.get("district", "Chennai")
                    dist_idx = MASTER_DISTRICTS_TN.index(cur_loc) if cur_loc in MASTER_DISTRICTS_TN else 13
                    eg_loc = st.selectbox("Location / District *", MASTER_DISTRICTS_TN, index=dist_idx, key="guide_prof_dist")
                    eg_exp = st.text_input("Primary Advisory Expertise *", value=cur_data.get("expertise", ""), placeholder="e.g. PMEGP Loan Specialist, MSME Scaling")
                eg_bio = st.text_area("Professional Background & Certifications", value=cur_data.get("bio", ""), placeholder="Describe your background, years of experience, and specialized certifications...", height=100)

                if st.form_submit_button("SAVE PROFILE CHANGES", type="primary", use_container_width=True):
                    if eg_name.strip() and eg_exp.strip():
                        upd_p, upd_err = update_mentor_profile(
                            user_id=guide_id,
                            full_name=eg_name.strip(),
                            phone=eg_phone.strip(),
                            district=eg_loc,
                            expertise=eg_exp.strip(),
                            bio=eg_bio.strip()
                        )
                        if upd_p:
                            st.success("Your Guide profile has been updated successfully!")
                            st.rerun()
                        else:
                            st.error(upd_err or "Failed to update profile.")
                    else:
                        st.warning("Please fill in your name and primary expertise.")

        st.markdown("#### 📜 Mentorship Assignment & Transition History")
        st.markdown("<p style='color:#64748B; font-size:0.85rem;'>Historical record of students assigned to your guidance roster, including administrative reassignments.</p>", unsafe_allow_html=True)

        history_rows = get_assignment_history(mentor_id=guide_id)
        if not history_rows:
            st.info("No transition history recorded yet.")
        else:
            for h in history_rows:
                act = h.get("action", "ASSIGNED")
                act_color = "#10b981" if act == "ASSIGNED" else "#f59e0b" if act == "REPLACED" else "#ef4444"
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="background:{act_color}; color:#fff; font-size:0.7rem; font-weight:800; padding:2px 6px; border-radius:4px; margin-right:6px;">{act}</span>
                        <strong style="color:#0F172A; font-size:0.9rem;">{h.get('aspirant_name', 'Student')}</strong>
                        <span style="color:#64748B; font-size:0.8rem; margin-left:6px;">({h.get('notes') or 'No notes'})</span>
                    </div>
                    <div style="color:#94A3B8; font-size:0.8rem;">{str(h.get('created_at',''))[:16]}</div>
                </div>
                """, unsafe_allow_html=True)
