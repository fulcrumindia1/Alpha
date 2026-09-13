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
from datetime import date
from services.relationships import get_assigned_aspirants_for_guide, get_aspirant_mentors
from services.profiles import get_profile
from services.journey import get_journey_timeline, add_guide_contribution, soft_delete_event
from services.schemes import (
    list_schemes,
    evaluate_scheme_for_aspirant,
    release_scheme_to_aspirant,
    withdraw_scheme_release,
    get_guide_scheme_releases
)
from services.help_requests import (
    list_guide_requests,
    guide_respond_request,
    check_and_escalate_overdue_requests
)

def render_guide_portal(user_profile: dict):
    guide_id = user_profile["id"]
    guide_name = user_profile.get("full_name", "Mentor")

    # Run auto-escalation check lazily
    try:
        check_and_escalate_overdue_requests()
    except Exception:
        pass

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

    main_tabs = st.tabs(["👥 My Aspirants", "💬 Help Requests"])

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

                # 4 Dedicated Context Tabs for Selected Aspirant
                subtabs = st.tabs([
                    "👤 Profile",
                    "🎬 Journey",
                    "🤝 Assigned Mentors",
                    "🏦 Scheme Matches"
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
                                m_topic = st.selectbox("Topic / Domain", ["Pricing & Model", "Market Strategy", "PMEGP Loan Preparation", "Customer Discovery", "Unit Economics", "Operations"])
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
                    timeline = get_journey_timeline(selected_asp_id)
                    if not timeline:
                        st.info("No journey events recorded yet for this founder.")
                    else:
                        for event in timeline:
                            actor_role = event.get("actor_role", "aspirant")
                            actor_name = event.get("actor_name") or "Mentor"
                            ev_data = event.get("event_data", {})
                            raw_title = ev_data.get("title") or event.get("event_type") or "Milestone"
                            raw_desc = ev_data.get("description", "")
                            title = html.escape(str(raw_title))
                            desc = html.escape(str(raw_desc)).replace("\n", "<br>")
                            date_display = str(event.get("event_date", ""))[:10]

                            badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                            col_t, col_b, col_act = st.columns([1.2, 5, 0.8])
                            with col_t:
                                st.markdown(f"""
                                <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                                <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{actor_role}</span>
                                """, unsafe_allow_html=True)
                            with col_b:
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                    <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">{title}</div>
                                    <div style="color:#334155; font-size:0.9rem; margin-top:0.3rem; line-height:1.5;">{desc}</div>
                                    <div style="font-size:0.75rem; color:#64748B; margin-top:0.4rem;">Contributor: {actor_name} ({actor_role})</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_act:
                                if event.get("actor_id") == guide_id and actor_role == "guide":
                                    if st.button("🗑️", key=f"guide_del_{event['id']}", help="Delete your contribution"):
                                        soft_delete_event(event["id"], guide_id, "guide")
                                        st.rerun()

                # ─────────────────────────────────────────────────────────
                # SUBTAB 3: ASSIGNED MENTORS
                # ─────────────────────────────────────────────────────────
                with subtabs[2]:
                    st.markdown(f"### Guidance Team for {curr_asp['full_name']}")
                    mentors = get_aspirant_mentors(selected_asp_id)
                    m_guide = mentors.get("guide")
                    m_sme = mentors.get("sme")

                    col_mg1, col_mg2 = st.columns(2)
                    with col_mg1:
                        st.markdown("#### 🧭 Assigned Guide")
                        if m_guide:
                            gp = m_guide.get("profile_data", {})
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:12px; padding:1.2rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                                <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{m_guide.get('full_name')}</div>
                                <div style="color:#059669; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Dedicated Enterprise Mentor</div>
                                <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Location:</strong> {m_guide.get('district', 'Tamil Nadu')}</p>
                                <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Expertise:</strong> {gp.get('expertise', 'Enterprise Guidance')}</p>
                                <p style="font-size:0.82rem; color:#64748B; margin-top:0.5rem;"><em>"{gp.get('bio', 'Assigned by Administrator')}"</em></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("No Guide assigned.")

                    with col_mg2:
                        st.markdown("#### 🔬 Assigned Domain SME")
                        if m_sme:
                            sp = m_sme.get("profile_data", {})
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:12px; padding:1.2rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                                <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{m_sme.get('full_name')}</div>
                                <div style="color:#D97706; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Subject Matter Expert</div>
                                <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Specialization:</strong> {sp.get('expertise', 'Technical Advisory')}</p>
                                <p style="font-size:0.88rem; color:#334155; margin-bottom:4px;"><strong>Industry:</strong> {sp.get('industry', 'Advisory')}</p>
                                <p style="font-size:0.82rem; color:#64748B; margin-top:0.5rem;"><em>"{sp.get('bio', 'Technical Specialist')}"</em></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("No Domain SME assigned.")

                # ─────────────────────────────────────────────────────────
                # SUBTAB 4: SCHEME MATCHES (THE GATEKEEPER WORKSPACE)
                # ─────────────────────────────────────────────────────────
                with subtabs[3]:
                    st.markdown("### 🏦 Scheme Gatekeeper Workspace")
                    st.markdown(f"<p style='color:#64748B; font-size:0.9rem;'>Evaluate schemes from the master catalogue against <strong>{curr_asp['full_name']}</strong>'s profile, examine private insider intelligence & red flags, and release curated opportunities.</p>", unsafe_allow_html=True)

                    # 1. Master Catalogue Search & Filter
                    c_s1, c_s2, c_s3 = st.columns([2.5, 1.2, 1.2])
                    with c_s1:
                        g_sc_search = st.text_input("🔍 Search Master Catalogue", placeholder="e.g. PMEGP, TANSEED, NEEDS, MUDRA...", key="g_sc_search")
                    with c_s2:
                        g_sc_cat = st.selectbox("Category", ["ALL", "Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"], key="g_sc_cat")
                    with c_s3:
                        g_sc_stage = st.selectbox("Stage", ["ALL", "Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"], key="g_sc_stage")

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
                                        <div style="font-size:1.2rem; font-weight:800; color:#FFFFFF;">{html.escape(eval_scheme.get('name','Untitled Scheme'))}</div>
                                        <div style="font-size:0.85rem; color:#94A3B8; margin-top:2px;">
                                            {html.escape(eval_scheme.get('agency',''))} · <span style="color:#C4B5FD; font-weight:700;">{html.escape(eval_scheme.get('funding_type','Grant'))}</span> · <span style="color:#34D399; font-weight:700;">{html.escape(eval_scheme.get('amount',''))}</span>
                                        </div>
                                    </div>
                                    <span style="background:{score_color}; color:#ffffff; font-weight:800; font-size:0.95rem; padding:4px 14px; border-radius:12px;">{score}% Match ({status_label})</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Match Reasons checklist & Eligibility
                            reasons = evaluation.get("match_reasons", [])
                            reasons_html = "".join([f"<li style='margin-bottom:3px;'><strong style='color:#10b981;'>✓</strong> {html.escape(r)}</li>" for r in reasons])
                            st.markdown(f"""
                            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.75rem;">
                                <strong style="color:#166534; font-size:0.9rem;">Match Reasoning & Profile Alignment:</strong>
                                <ul style="font-size:0.85rem; color:#14532D; margin:0.4rem 0 0 1rem; padding:0;">{reasons_html}</ul>
                            </div>
                            """, unsafe_allow_html=True)

                            # Guide-Only Private Intelligence
                            agenda_text = eval_scheme.get("hidden_agenda")
                            if isinstance(agenda_text, list):
                                agenda_str = "<br>".join(f"• {html.escape(str(x))}" for x in agenda_text if str(x).strip())
                            else:
                                agenda_str = html.escape(str(agenda_text or "No hidden agenda specified."))

                            flags_text = eval_scheme.get("red_flags")
                            if isinstance(flags_text, list):
                                flags_str = "<br>".join(f"• {html.escape(str(x))}" for x in flags_text if str(x).strip())
                            else:
                                flags_str = html.escape(str(flags_text or "No specific red flags identified."))

                            st.markdown(f"""
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:1rem;">
                                <div style="background:rgba(245,158,11,0.12); border-left:4px solid #F59E0B; padding:0.85rem; border-radius:0 8px 8px 0; font-size:0.84rem; color:#FCD34D; line-height:1.45;">
                                    <div style="font-weight:800; color:#FBBF24; margin-bottom:4px; font-size:0.85rem;">🤫 INSIDER INTELLIGENCE / HIDDEN AGENDA (Guide Only):</div>
                                    <div>{agenda_str}</div>
                                </div>
                                <div style="background:rgba(239,68,68,0.12); border-left:4px solid #EF4444; padding:0.85rem; border-radius:0 8px 8px 0; font-size:0.84rem; color:#FCA5A5; line-height:1.45;">
                                    <div style="font-weight:800; color:#F87171; margin-bottom:4px; font-size:0.85rem;">⚠️ RED FLAGS / STRICT CAUTIONS (Guide Only):</div>
                                    <div>{flags_str}</div>
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
                                            st.success(f"Successfully released '{eval_scheme.get('name')}' to {curr_asp['full_name']}!")
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
                                    <div style="font-weight:800; font-size:1.05rem; color:#0F172A;">{html.escape(rel.get('scheme_name') or 'Scheme')}</div>
                                    <div style="font-size:0.84rem; color:#64748B; margin:2px 0 6px 0;">
                                        {html.escape(rel.get('scheme_agency') or '')} · Released: {str(rel.get('released_at',''))[:10]}
                                    </div>
                                    <div style="font-size:0.86rem; color:#334155; background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0;">
                                        <strong style="color:#7C3AED;">Recommendation Note:</strong> {html.escape(rel.get('guide_recommendation') or 'No note provided')}
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
                                    <div style="font-weight:700; color:#475569;">{html.escape(w.get('scheme_name') or 'Scheme')}</div>
                                    <div style="font-size:0.8rem; color:#94A3B8;">Withdrawn: {str(w.get('withdrawn_at',''))[:16]}</div>
                                </div>
                                """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB 2: GUIDE HELP REQUESTS QUEUE
    # ─────────────────────────────────────────────────────────────
    with main_tabs[1]:
        st.subheader("Assigned Help Requests")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Support tickets submitted by your assigned entrepreneurs. Tickets pending for more than 7 days automatically escalate to the Administrator.</p>", unsafe_allow_html=True)

        col_f1, col_f2 = st.columns([3, 1])
        with col_f2:
            status_filter = st.selectbox("Status Filter", ["ALL", "OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED"], key="guide_hr_status_filter")

        guide_tickets = list_guide_requests(guide_id)
        if status_filter != "ALL":
            guide_tickets = [t for t in guide_tickets if t.get("status") == status_filter]

        if not guide_tickets:
            st.info("No help requests found in this queue.")
        else:
            for t in guide_tickets:
                t_status = t.get("status", "OPEN")
                st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status == "IN_PROGRESS" else "#10b981" if t_status == "RESOLVED" else "#ef4444"
                is_escalated = (t_status == "ESCALATED")

                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid {'#EF4444' if is_escalated else '#E2E8F0'}; border-left:4px solid {st_color}; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:1.1rem; font-weight:800; color:#0F172A;">{html.escape(t.get('subject','Support Ticket'))}</span>
                            <span style="font-size:0.75rem; font-weight:800; background:{st_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:8px;">{t_status}</span>
                            <span style="font-size:0.75rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get('priority','MEDIUM')}</span>
                        </div>
                        <div style="font-size:0.8rem; color:#64748B;">{str(t.get('created_at',''))[:16]}</div>
                    </div>
                    <div style="font-size:0.85rem; color:#64748B; margin:4px 0;">
                        From: <strong style="color:#0F172A;">{html.escape(t.get('aspirant_name') or 'Entrepreneur')}</strong> ({html.escape(t.get('aspirant_email') or '')})
                    </div>
                    <div style="font-size:0.9rem; color:#334155; margin-top:0.4rem; line-height:1.45;">
                        {html.escape(t.get('message',''))}
                    </div>
                    {f'''<div style="background:#FEF2F2; border:1px solid #F87171; border-radius:6px; padding:0.5rem 0.8rem; color:#991B1B; font-weight:700; font-size:0.84rem; margin-top:0.5rem;">
                        ⚠️ ESCALATED TO ADMIN: {html.escape(t.get('escalation_reason') or 'Automatically escalated after 7 days without resolution.')}
                    </div>''' if is_escalated else ''}
                    {f'''<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:3px solid #10b981; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#166534; margin-top:0.5rem;">
                        <strong>Guide Response:</strong> {html.escape(t.get('guide_response') or '')}
                    </div>''' if t.get('guide_response') else ''}
                </div>
                """, unsafe_allow_html=True)

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
