"""
pages/sme.py — SME Dashboard for FULCRUM-INDIA (Cluster A)
=========================================================
SME Experience:
- Overview of assigned specialized advisory cases (GST, FSSAI, Patents, Legal).
- Inspect Aspirant venture profile and full chronological Journey.
- [ + Add Journey Entry ]: Contribute technical domain support.
- Manage/delete only their own contributions.
"""

import streamlit as st
import html
from datetime import date
from services.relationships import get_assigned_aspirants_for_sme, get_assignment_history, get_aspirant_mentors
from services.profiles import get_profile, update_mentor_profile
from services.journey import get_journey_timeline, add_sme_contribution, soft_delete_event, get_standard_role_label
from services.constants import MASTER_DISTRICTS_TN
from services.help_requests import list_sme_requests, sme_respond_request

def render_sme_portal(user_profile: dict):
    sme_id = user_profile["id"]
    sme_name = user_profile.get("full_name", "Specialist")
    domain_focus = user_profile.get("profile_data", {}).get("expertise") or "Domain Advisory"

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #E2E8F0;">
        <div>
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#D97706;">SME Advisory Portal</div>
            <h1 style="font-size:2rem; font-weight:800; margin:0; color:#0F172A;">Welcome, {sme_name}</h1>
            <p style="font-size:0.95rem; color:#475569; margin-top:0.25rem;">
                Subject Matter Expertise & Specialized Technical Advisory Workspace · {domain_focus}
            </p>
        </div>
        <div style="text-align:right;">
            <span style="display:inline-block; padding:4px 14px; border-radius:12px; font-size:0.85rem; font-weight:700; background:#FFFBEB; color:#D97706; border:1px solid #FDE68A;">
                Role: Verified SME
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    assigned_aspirants = get_assigned_aspirants_for_sme(sme_id)

    tabs = st.tabs([
        "👥 My Assigned Cases",
        "💬 All Consultations Overview",
        "👤 My Profile"
    ])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: MY ASSIGNED CASES (CASELOAD WORKSPACE)
    # ─────────────────────────────────────────────────────────────
    with tabs[0]:
        if not assigned_aspirants:
            st.info("No cases currently assigned to you. When the Admin assigns an entrepreneur to your advisory roster, or when an entrepreneur submits a domain consultation query, they will appear here.")
        else:
            asp_options = {
                a["id"]: f"{a['full_name']} — {a.get('profile_data',{}).get('business',{}).get('business_name','Enterprise')} ({a.get('district', 'Tamil Nadu')})"
                for a in assigned_aspirants
            }
            default_idx = 0
            if st.session_state.get("sme_selected_aspirant") in asp_options:
                default_idx = list(asp_options.keys()).index(st.session_state["sme_selected_aspirant"])

            selected_asp_id = st.selectbox(
                "Select Entrepreneur for Domain Advisory",
                list(asp_options.keys()),
                format_func=lambda x: asp_options[x],
                index=default_idx,
                key="sme_asp_select"
            )
            st.session_state["sme_selected_aspirant"] = selected_asp_id

            curr_asp = next((a for a in assigned_aspirants if a["id"] == selected_asp_id), None)
            if curr_asp:
                st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

                # Calculate direct consultations from this mentee directed to this SME
                all_sme_tickets = list_sme_requests(sme_id) or []
                asp_tickets = [t for t in all_sme_tickets if t.get("aspirant_id") == selected_asp_id]
                open_cnt = sum(1 for t in asp_tickets if t.get("status") in ["OPEN", "IN_PROGRESS"])
                consult_label = f"💬 Consultations ({open_cnt} Open)" if open_cnt > 0 else "💬 Consultations"

                # 4 Dedicated Subtabs for Selected Aspirant (No Scheme Matches for SME!)
                subtabs = st.tabs([
                    "👤 Profile",
                    "🎬 Journey",
                    "🤝 Guidance Team",
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

                    st.markdown("#### 2. Professional Background")
                    cpr1, cpr2 = st.columns(2)
                    with cpr1:
                        st.markdown(f"**Education / Qualification:** {prof.get('education', 'N/A')}")
                        st.markdown(f"**Key Skills:** {prof.get('skills', 'N/A')}")
                    with cpr2:
                        st.markdown(f"**Experience:** {prof.get('experience', 'N/A')}")
                        st.markdown(f"**Certifications / Training:** {prof.get('certifications', 'N/A')}")

                    st.markdown("---")

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

                    st.markdown("---")

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
                # SUBTAB 2: ASPIRANT JOURNEY & DOMAIN CONTRIBUTION
                # ─────────────────────────────────────────────────────────
                with subtabs[1]:
                    st.markdown(f"### Domain Mentorship: {curr_asp['full_name']}")

                    with st.expander(f"➕ Log Domain Guidance for {curr_asp['full_name']}'s Journey", expanded=False):
                        with st.form("form_sme_add_entry_sub"):
                            col_sm1, col_sm2 = st.columns(2)
                            with col_sm1:
                                s_title = st.text_input("Title / Advisory Topic", placeholder="e.g. GST Registration & Invoicing Audit")
                                s_domain_sel = st.selectbox("Specialized Domain", [
                                    "GST & Taxation",
                                    "FSSAI & Food Standards",
                                    "Patents & Trademark",
                                    "Labor & Statutory Compliance",
                                    "Export / Import Code",
                                    "Technical Architecture",
                                    "Other / Specialized Compliance (Specify)"
                                ])
                                s_domain = s_domain_sel
                                if s_domain_sel == "Other / Specialized Compliance (Specify)":
                                    s_domain_custom = st.text_input("Specify Advisory Domain *", placeholder="e.g. Environmental Clearance (PCB)", key="sme_custom_domain_sub")
                                    if s_domain_custom and s_domain_custom.strip():
                                        s_domain = s_domain_custom.strip()
                            with col_sm2:
                                s_date = st.date_input("Advisory Date", value=date.today())
                            s_desc = st.text_area("Detailed Recommendation / Deliverable", placeholder="Explained GST threshold exemptions, set up HSN codes for millet flour, and verified bank statement reconciliation.")

                            if st.form_submit_button("SAVE DOMAIN CONTRIBUTION", type="primary"):
                                if s_title and s_desc:
                                    ev, err = add_sme_contribution(
                                        aspirant_id=selected_asp_id,
                                        sme_id=sme_id,
                                        title=s_title,
                                        description=s_desc,
                                        domain=s_domain,
                                        event_date=s_date.isoformat()
                                    )
                                    if ev:
                                        st.success(f"Added domain guidance to {curr_asp['full_name']}'s Journey!")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to record contribution.")
                                else:
                                    st.warning("Please fill in both title and recommendation.")

                    st.markdown(f"#### Complete Journey Narrative Spine")
                    timeline = get_journey_timeline(selected_asp_id)
                    if not timeline:
                        st.info("No journey events recorded yet.")
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
                            raw_title = ev_data.get("title") or event.get("event_type") or "Advisory Event"
                            raw_desc = ev_data.get("description", "")
                            title = html.escape(str(raw_title))
                            desc = html.escape(str(raw_desc)).replace("\n", "<br>")
                            date_display = str(event.get("event_date", ""))[:10]

                            badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                            inc = event.get("included_in_roadmap", True)
                            if inc is False:
                                status_badge_html = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:2px 8px; border-radius:6px; margin-left:8px;">⚠️ Founder Marked: Not Needed</span>'
                            else:
                                status_badge_html = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; padding:2px 8px; border-radius:6px; margin-left:8px;">✓ Active on Founder Roadmap</span>'

                            col_t, col_b, col_act = st.columns([1.2, 5, 0.8])
                            with col_t:
                                st.markdown(f"""
                                <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                                <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{std_role}</span>
                                """, unsafe_allow_html=True)
                            with col_b:
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                        <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">{title}</div>
                                        <div>{status_badge_html}</div>
                                    </div>
                                    <div style="color:#334155; font-size:0.9rem; margin-top:0.3rem; line-height:1.5;">{desc}</div>
                                    <div style="font-size:0.75rem; color:#64748B; margin-top:0.4rem;">Contributor: <strong>{actor_name}</strong> ({std_role})</div>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_act:
                                if event.get("actor_id") == sme_id and actor_role == "sme":
                                    if st.button("🗑️", key=f"sme_del_sub_{event['id']}", help="Delete your contribution"):
                                        soft_delete_event(event["id"], sme_id, "sme")
                                        st.rerun()

                # ─────────────────────────────────────────────────────────
                # SUBTAB 3: GUIDANCE TEAM
                # ─────────────────────────────────────────────────────────
                with subtabs[2]:
                    st.markdown(f"### Guidance Team for {curr_asp['full_name']}")
                    st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Institutional mentors and specialized domain experts collaborating on this entrepreneur's advisory roadmap.</p>", unsafe_allow_html=True)
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
                                is_self = (sp_item.get("id") == sme_id)
                                border_col = "#D97706" if is_self else "#CBD5E1"
                                self_badge = '<span style="background:#FEF3C7; color:#B45309; font-size:0.7rem; font-weight:800; padding:2px 6px; border-radius:4px; margin-left:6px;">YOU</span>' if is_self else ''
                                st.markdown(f"""
                                <div style="background:#FFFFFF; border:1px solid {border_col}; border-left:4px solid #f59e0b; border-radius:12px; padding:1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                                    <div style="font-size:1.15rem; font-weight:800; color:#0F172A;">{s_name}{self_badge}</div>
                                    <div style="color:#D97706; font-weight:600; font-size:0.85rem; margin-bottom:0.4rem;">{s_exp} · {s_dist}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No Domain SMEs assigned.")

                # ─────────────────────────────────────────────────────────
                # SUBTAB 4: DIRECT CONSULTATIONS & DOMAIN QUERIES
                # ─────────────────────────────────────────────────────────
                with subtabs[3]:
                    st.subheader(f"Domain Consultations: {curr_asp['full_name']}")
                    st.markdown(f"<p style='color:#64748B; font-size:0.9rem;'>Technical and compliance consultation requests submitted by <strong>{curr_asp['full_name']}</strong>.</p>", unsafe_allow_html=True)

                    if not asp_tickets:
                        st.info(f"No domain advisory requests currently recorded from {curr_asp['full_name']}.")
                    else:
                        for t in asp_tickets:
                            t_status = t.get("status", "OPEN")
                            st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status == "IN_PROGRESS" else "#10b981" if t_status == "RESOLVED" else "#ef4444"

                            escaped_subject = html.escape(t.get('subject', 'Advisory Request'))
                            escaped_asp_name = html.escape(t.get('aspirant_name') or curr_asp.get('full_name', 'Entrepreneur'))
                            escaped_asp_email = html.escape(t.get('aspirant_email') or curr_asp.get('email', ''))
                            escaped_message = html.escape(t.get('message', '')).replace('\n', '<br>')

                            sme_resp_html = ""
                            if t.get('sme_response') or t.get('guide_response'):
                                r_text = t.get('sme_response') or t.get('guide_response') or ""
                                sme_resp_html = f'<div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:3px solid #f59e0b; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#92400E; margin-top:0.5rem;"><strong>Your Specialist Advisory Note:</strong> {html.escape(r_text)}</div>'

                            card_html = (
                                f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {st_color}; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                                f'<div><span style="font-size:1.1rem; font-weight:800; color:#0F172A;">{escaped_subject}</span>'
                                f'<span style="font-size:0.75rem; font-weight:800; background:{st_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:8px;">{t_status}</span>'
                                f'<span style="font-size:0.75rem; font-weight:700; background:#FEF3C7; color:#B45309; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("category","GENERAL")}</span>'
                                f'<span style="font-size:0.75rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("priority","MEDIUM")}</span></div>'
                                f'<div style="font-size:0.8rem; color:#64748B;">{str(t.get("created_at",""))[:16]}</div>'
                                f'</div>'
                                f'<div style="font-size:0.85rem; color:#64748B; margin:4px 0;">From: <strong style="color:#0F172A;">{escaped_asp_name}</strong> ({escaped_asp_email})</div>'
                                f'<div style="font-size:0.9rem; color:#334155; margin-top:0.4rem; line-height:1.45;">{escaped_message}</div>'
                                f'{sme_resp_html}'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                            if t_status in ["OPEN", "IN_PROGRESS"]:
                                with st.expander(f"💬 Provide Advisory Guidance for '{t.get('subject')}'", expanded=False):
                                    with st.form(f"form_sme_resp_sub_{t['id']}"):
                                        c_sr1, c_sr2 = st.columns([1, 2])
                                        with c_sr1:
                                            new_sme_st = st.selectbox("Update Status", ["IN_PROGRESS", "RESOLVED"], key=f"sel_sme_st_sub_{t['id']}")
                                        with c_sr2:
                                            sme_resp_text = st.text_area("Advisory Guidance / Technical Memorandum *", placeholder="Provide technical recommendations, statutory compliance steps, or confirm resolution...", height=80, key=f"txt_sme_resp_sub_{t['id']}")

                                        if st.form_submit_button("Submit Guidance & Update Ticket", type="primary"):
                                            if not sme_resp_text.strip():
                                                st.warning("Please enter your advisory response.")
                                            else:
                                                ok, err = sme_respond_request(t["id"], sme_id, new_sme_st, sme_resp_text.strip())
                                                if ok:
                                                    st.success("Advisory response recorded and student notified!")
                                                    st.rerun()
                                                else:
                                                    st.error(err or "Failed to record response.")

    # ─────────────────────────────────────────────────────────────
    # TAB 2: SME ALL CONSULTATIONS OVERVIEW
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("💬 All Domain Consultations Overview")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Specialized consultation queries submitted by entrepreneurs requiring your domain expertise across your entire caseload.</p>", unsafe_allow_html=True)

        col_sf1, col_sf2 = st.columns([3, 1])
        with col_sf2:
            sme_status_filter = st.selectbox("Filter Status", ["ALL", "OPEN", "IN_PROGRESS", "RESOLVED"], key="sme_hr_status_filter")

        sme_tickets = list_sme_requests(sme_id)
        if sme_status_filter != "ALL":
            sme_tickets = [t for t in (sme_tickets or []) if t.get("status") == sme_status_filter]

        if not sme_tickets:
            st.info("No domain advisory requests currently pending for your specialization.")
        else:
            for t in sme_tickets:
                t_status = t.get("status", "OPEN")
                st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status == "IN_PROGRESS" else "#10b981" if t_status == "RESOLVED" else "#ef4444"

                escaped_subject = html.escape(t.get('subject', 'Advisory Request'))
                escaped_asp_name = html.escape(t.get('aspirant_name') or 'Entrepreneur')
                escaped_asp_email = html.escape(t.get('aspirant_email') or '')
                escaped_message = html.escape(t.get('message', '')).replace('\n', '<br>')

                sme_resp_html = ""
                if t.get('sme_response') or t.get('guide_response'):
                    r_text = t.get('sme_response') or t.get('guide_response') or ""
                    sme_resp_html = f'<div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:3px solid #f59e0b; border-radius:0 6px 6px 0; padding:0.5rem 0.8rem; font-size:0.86rem; color:#92400E; margin-top:0.5rem;"><strong>Specialist Advisory Note:</strong> {html.escape(r_text)}</div>'

                card_html = (
                    f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {st_color}; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.8rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<div><span style="font-size:1.1rem; font-weight:800; color:#0F172A;">{escaped_subject}</span>'
                    f'<span style="font-size:0.75rem; font-weight:800; background:{st_color}; color:#ffffff; padding:2px 8px; border-radius:6px; margin-left:8px;">{t_status}</span>'
                    f'<span style="font-size:0.75rem; font-weight:700; background:#FEF3C7; color:#B45309; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("category","GENERAL")}</span>'
                    f'<span style="font-size:0.75rem; font-weight:700; background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; margin-left:4px;">{t.get("priority","MEDIUM")}</span></div>'
                    f'<div style="font-size:0.8rem; color:#64748B;">{str(t.get("created_at",""))[:16]}</div>'
                    f'</div>'
                    f'<div style="font-size:0.85rem; color:#64748B; margin:4px 0;">From: <strong style="color:#0F172A;">{escaped_asp_name}</strong> ({escaped_asp_email})</div>'
                    f'<div style="font-size:0.9rem; color:#334155; margin-top:0.4rem; line-height:1.45;">{escaped_message}</div>'
                    f'{sme_resp_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                col_btn_sc, _ = st.columns([1, 3])
                with col_btn_sc:
                    if st.button("Open Case →", key=f"btn_open_case_ov_{t['id']}_{t.get('aspirant_id')}"):
                        st.session_state["sme_selected_aspirant"] = t.get("aspirant_id")
                        st.rerun()

                if t_status in ["OPEN", "IN_PROGRESS"]:
                    with st.expander(f"💬 Provide Advisory Guidance for '{t.get('subject')}'", expanded=False):
                        with st.form(f"form_sme_resp_ov_{t['id']}"):
                            c_sr1, c_sr2 = st.columns([1, 2])
                            with c_sr1:
                                new_sme_st = st.selectbox("Update Status", ["IN_PROGRESS", "RESOLVED"], key=f"sel_sme_st_ov_{t['id']}")
                            with c_sr2:
                                sme_resp_text = st.text_area("Advisory Guidance / Technical Memorandum *", placeholder="Provide technical recommendations, statutory compliance steps, or confirm resolution...", height=80, key=f"txt_sme_resp_ov_{t['id']}")

                            if st.form_submit_button("Submit Guidance & Update Ticket", type="primary"):
                                if not sme_resp_text.strip():
                                    st.warning("Please enter your advisory response.")
                                else:
                                    ok, err = sme_respond_request(t["id"], sme_id, new_sme_st, sme_resp_text.strip())
                                    if ok:
                                        st.success("Advisory response recorded and student notified!")
                                        st.rerun()
                                    else:
                                        st.error(err or "Failed to record response.")

    # ─────────────────────────────────────────────────────────────
    # TAB 3: SME PROFILE & ASSIGNMENT HISTORY
    # ─────────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("👤 My SME Specialist Profile")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Manage your domain advisory credentials, industry specializations, and view your case assignment transitions.</p>", unsafe_allow_html=True)

        cur_profile = get_profile(sme_id) or user_profile
        cur_data = cur_profile.get("profile_data", {})
        if isinstance(cur_data, str):
            import json
            try:
                cur_data = json.loads(cur_data)
            except Exception:
                cur_data = {}

        # Profile Card
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:0 12px 12px 0; padding:1.25rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <h3 style="margin:0; color:#0F172A; font-size:1.35rem;">{cur_profile.get('full_name')}</h3>
                    <div style="color:#D97706; font-weight:700; font-size:0.9rem; margin-top:2px;">Subject Matter Expert · {cur_profile.get('district', 'Tamil Nadu')}</div>
                    <div style="color:#475569; font-size:0.85rem; margin-top:0.35rem;">
                        <strong>Email:</strong> {cur_profile.get('email')} | <strong>Phone:</strong> {cur_profile.get('phone') or 'Not Set'}
                    </div>
                    <div style="color:#334155; font-size:0.88rem; margin-top:0.4rem;">
                        <strong>Specialization Domain:</strong> {cur_data.get('expertise', 'Technical Compliance & Advisory')}
                    </div>
                    <div style="color:#334155; font-size:0.85rem; margin-top:0.2rem;">
                        <strong>Industry Focus:</strong> {cur_data.get('industry', 'Multi-Sector')}
                    </div>
                    {f'<div style="font-size:0.85rem; color:#64748B; margin-top:0.4rem; font-style:italic;">"{cur_data.get("bio")}"</div>' if cur_data.get('bio') else ''}
                </div>
                <span style="background:#FFFBEB; color:#D97706; border:1px solid #FDE68A; font-size:0.75rem; font-weight:800; padding:3px 10px; border-radius:8px;">VERIFIED SME</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("✏️ Edit My Specialist Profile & Credentials", expanded=False):
            with st.form("form_edit_sme_profile"):
                col_sp1, col_sp2 = st.columns(2)
                with col_sp1:
                    es_name = st.text_input("Full Name *", value=cur_profile.get("full_name", ""))
                    es_phone = st.text_input("Phone Number *", value=cur_profile.get("phone", ""), placeholder="e.g. 9876543212")
                with col_sp2:
                    cur_loc = cur_profile.get("district", "Chennai")
                    dist_idx = MASTER_DISTRICTS_TN.index(cur_loc) if cur_loc in MASTER_DISTRICTS_TN else 13
                    es_loc = st.selectbox("Location / District *", MASTER_DISTRICTS_TN, index=dist_idx, key="sme_prof_dist")
                    es_exp = st.text_input("Specialization Domain *", value=cur_data.get("expertise", ""), placeholder="e.g. GST Auditing, Taxation, Corporate Compliance")
                es_ind = st.text_input("Industry Focus", value=cur_data.get("industry", ""), placeholder="e.g. Food Processing, Export, Manufacturing")
                es_bio = st.text_area("Professional Summary & Certifications", value=cur_data.get("bio", ""), placeholder="Describe your credentials, advisory experience, and certifications...", height=100)

                if st.form_submit_button("SAVE PROFILE CHANGES", type="primary", use_container_width=True):
                    if es_name.strip() and es_exp.strip():
                        upd_p, upd_err = update_mentor_profile(
                            user_id=sme_id,
                            full_name=es_name.strip(),
                            phone=es_phone.strip(),
                            district=es_loc,
                            expertise=es_exp.strip(),
                            bio=es_bio.strip(),
                            industry=es_ind.strip()
                        )
                        if upd_p:
                            st.success("Your SME profile has been updated successfully!")
                            st.rerun()
                        else:
                            st.error(upd_err or "Failed to update profile.")
                    else:
                        st.warning("Please fill in your name and specialization domain.")

        st.markdown("#### 📜 Case Assignment & Transition History")
        st.markdown("<p style='color:#64748B; font-size:0.85rem;'>Historical record of specialized cases assigned to you, including administrative reassignments.</p>", unsafe_allow_html=True)

        sme_history_rows = get_assignment_history(mentor_id=sme_id)
        if not sme_history_rows:
            st.info("No transition history recorded yet.")
        else:
            for h in sme_history_rows:
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
