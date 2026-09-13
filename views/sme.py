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
from services.relationships import get_assigned_aspirants_for_sme
from services.journey import get_journey_timeline, add_sme_contribution, soft_delete_event

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

    tabs = st.tabs(["📑 Assigned Cases", "🔬 Domain Journey Contributions"], key="sme_portal_tabs")

    # ─────────────────────────────────────────────────────────────
    # TAB 1: ASSIGNED CASES
    # ─────────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Assigned Advisory Cases")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Entrepreneurs assigned to you by the Program Administrator for specialized technical or compliance advisory.</p>", unsafe_allow_html=True)

        if not assigned_aspirants:
            st.info("No cases currently assigned to you. When the Admin assigns an entrepreneur needing specialized domain advice, they will appear here.")
        else:
            for asp in assigned_aspirants:
                b_data = asp.get("profile_data", {}).get("business", {})
                b_name = b_data.get("business_name") or f"{asp.get('full_name')}'s Enterprise"
                b_sector = b_data.get("sector") or "General"

                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:0 12px 12px 0; padding:1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{asp.get('full_name')}</div>
                        <div style="color:#D97706; font-weight:600; font-size:0.9rem;">{b_name} · {b_sector}</div>
                        <div style="font-size:0.85rem; color:#475569; margin-top:0.3rem;">
                            <strong>District:</strong> {asp.get('district')} | <strong>Email:</strong> {asp.get('email')}
                        </div>
                        {f'<div style="font-size:0.8rem; color:#2563EB; margin-top:0.3rem;"><strong>Requisition Notes:</strong> {asp.get("assignment_notes")}</div>' if asp.get('assignment_notes') else ''}
                    </div>
                    """, unsafe_allow_html=True)
                with col_s2:
                    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
                    if st.button("Open Case →", key=f"btn_open_sme_case_{asp['id']}", use_container_width=True):
                        st.session_state["sme_selected_aspirant"] = asp["id"]
                        st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB 2: DOMAIN ADVISORY WORKSPACE
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        if not assigned_aspirants:
            st.info("No assigned cases to inspect.")
            return

        options = {a["id"]: f"{a['full_name']} — {a.get('profile_data',{}).get('business',{}).get('business_name','Enterprise')}" for a in assigned_aspirants}
        default_idx = 0
        if st.session_state.get("sme_selected_aspirant") in options:
            default_idx = list(options.keys()).index(st.session_state["sme_selected_aspirant"])

        selected_asp_id = st.selectbox("Select Entrepreneur Case", list(options.keys()), format_func=lambda x: options[x], index=default_idx)
        st.session_state["sme_selected_aspirant"] = selected_asp_id

        curr_asp = next((a for a in assigned_aspirants if a["id"] == selected_asp_id), None)
        if not curr_asp:
            return

        st.markdown("---")
        st.subheader(f"Advisory Workspace: {curr_asp['full_name']}")

        with st.expander(f"➕ Log Domain Guidance for {curr_asp['full_name']}'s Journey", expanded=True):
            with st.form("form_sme_add_entry"):
                col_sm1, col_sm2 = st.columns(2)
                with col_sm1:
                    s_title = st.text_input("Title / Advisory Topic", placeholder="e.g. GST Registration & Invoicing Audit")
                    s_domain = st.selectbox("Specialized Domain", ["GST & Taxation", "FSSAI & Food Standards", "Patents & Trademark", "Labor & Statutory Compliance", "Export / Import Code", "Technical Architecture"])
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

        # Timeline View
        st.markdown(f"#### {curr_asp['full_name']}'s Complete Journey")
        timeline = get_journey_timeline(selected_asp_id)
        if not timeline:
            st.info("No journey events recorded yet.")
        else:
            for event in timeline:
                actor_role = event.get("actor_role", "aspirant")
                actor_name = event.get("actor_name") or "Specialist"
                ev_data = event.get("event_data", {})
                raw_title = ev_data.get("title") or event.get("event_type") or "Advisory Event"
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
                    # SMEs can only delete their own contributions
                    if event.get("actor_id") == sme_id and actor_role == "sme":
                        if st.button("🗑️", key=f"sme_del_{event['id']}", help="Delete your contribution"):
                            soft_delete_event(event["id"], sme_id, "sme")
                            st.rerun()
