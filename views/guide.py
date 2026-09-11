"""
pages/guide.py — Guide Dashboard for FULCRUM-INDIA (Cluster A)
=============================================================
Guide Experience:
- Overview & Assigned Aspirants Directory
- Drill down into any assigned Aspirant:
  - View Aspirant profile and business background
  - View full chronological Journey
  - [ + Add Journey Entry ]: Log mentorship guidance & milestones
  - Manage/delete only their own contributions
"""

import streamlit as st
from datetime import date
from services.relationships import get_assigned_aspirants_for_guide
from services.journey import get_journey_timeline, add_guide_contribution, soft_delete_event

def render_guide_portal(user_profile: dict):
    guide_id = user_profile["id"]
    guide_name = user_profile.get("full_name", "Mentor")

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #E2E8F0;">
        <div>
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#059669;">Guide Portal</div>
            <h1 style="font-size:2rem; font-weight:800; margin:0; color:#0F172A;">Welcome, {guide_name}</h1>
            <p style="font-size:0.95rem; color:#475569; margin-top:0.25rem;">
                Dedicated Enterprise Guidance & Mentorship Workspace
            </p>
        </div>
        <div style="text-align:right;">
            <span style="display:inline-block; padding:4px 14px; border-radius:12px; font-size:0.85rem; font-weight:700; background:#ECFDF5; color:#059669; border:1px solid #A7F3D0;">
                Role: Verified Guide
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    assigned_aspirants = get_assigned_aspirants_for_guide(guide_id)

    tabs = st.tabs(["👥 My Aspirants", "🎬 Aspirant Journey Workspace"])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: MY ASPIRANTS DIRECTORY
    # ─────────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Assigned Entrepreneurs")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>These founders have been assigned to your mentorship roster by the Program Administrator.</p>", unsafe_allow_html=True)

        if not assigned_aspirants:
            st.info("No Aspirants are currently assigned to you. When the Admin assigns an entrepreneur to your queue, they will appear here.")
        else:
            for asp in assigned_aspirants:
                b_data = asp.get("profile_data", {}).get("business", {})
                b_name = b_data.get("business_name") or f"{asp.get('full_name')}'s Enterprise"
                b_sector = b_data.get("sector") or "General"
                b_stage = b_data.get("stage") or "Early Stage"

                col_a1, col_a2 = st.columns([3, 1])
                with col_a1:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{asp.get('full_name')}</div>
                        <div style="color:#059669; font-weight:600; font-size:0.9rem;">{b_name} · {b_sector}</div>
                        <div style="font-size:0.85rem; color:#475569; margin-top:0.3rem;">
                            <strong>District:</strong> {asp.get('district')} | <strong>Stage:</strong> {b_stage} | <strong>Email:</strong> {asp.get('email')}
                        </div>
                        {f'<div style="font-size:0.8rem; color:#D97706; margin-top:0.3rem;"><strong>Admin Notes:</strong> {asp.get("assignment_notes")}</div>' if asp.get('assignment_notes') else ''}
                    </div>
                    """, unsafe_allow_html=True)
                with col_a2:
                    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
                    if st.button("Open Journey →", key=f"btn_open_asp_{asp['id']}", use_container_width=True):
                        st.session_state["guide_selected_aspirant"] = asp["id"]
                        st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB 2: ASPIRANT JOURNEY WORKSPACE
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        if not assigned_aspirants:
            st.info("No assigned Aspirants to inspect.")
            return

        # Select which aspirant to inspect
        options = {a["id"]: f"{a['full_name']} — {a.get('profile_data',{}).get('business',{}).get('business_name','Enterprise')}" for a in assigned_aspirants}
        default_idx = 0
        if st.session_state.get("guide_selected_aspirant") in options:
            default_idx = list(options.keys()).index(st.session_state["guide_selected_aspirant"])

        selected_asp_id = st.selectbox("Select Entrepreneur", list(options.keys()), format_func=lambda x: options[x], index=default_idx)
        st.session_state["guide_selected_aspirant"] = selected_asp_id

        curr_asp = next((a for a in assigned_aspirants if a["id"] == selected_asp_id), None)
        if not curr_asp:
            return

        st.markdown("---")
        st.subheader(f"Mentorship Workspace: {curr_asp['full_name']}")

        # Form to contribute mentorship log
        with st.expander(f"➕ Log Mentorship Contribution to {curr_asp['full_name']}'s Journey", expanded=True):
            with st.form("form_guide_add_entry"):
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    m_title = st.text_input("Title / Milestone", placeholder="e.g. Business Model Discussion")
                    m_topic = st.selectbox("Topic / Domain", ["Pricing & Model", "Market Strategy", "PMEGP Loan Preparation", "Customer Discovery", "Unit Economics", "Operations"])
                with col_g2:
                    m_date = st.date_input("Session Date", value=date.today())
                m_desc = st.text_area("Guidance Notes / What was achieved?", placeholder="Helped founder refine unit pricing model and identify initial 10 customer prospects in Madurai district.")

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

        # Display Aspirant's Full Journey Timeline
        st.markdown(f"#### {curr_asp['full_name']}'s Complete Journey")
        timeline = get_journey_timeline(selected_asp_id)
        if not timeline:
            st.info("No journey events recorded yet for this founder.")
        else:
            for event in timeline:
                actor_role = event.get("actor_role", "aspirant")
                actor_name = event.get("actor_name") or "Mentor"
                ev_data = event.get("event_data", {})
                title = ev_data.get("title") or event.get("event_type")
                desc = ev_data.get("description", "")
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
                    # Guides can only delete their own contributions
                    if event.get("actor_id") == guide_id and actor_role == "guide":
                        if st.button("🗑️", key=f"guide_del_{event['id']}", help="Delete your contribution"):
                            soft_delete_event(event["id"], guide_id, "guide")
                            st.rerun()
