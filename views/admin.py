"""
pages/admin.py — Admin Control Tower for FULCRUM-INDIA (Cluster A)
=================================================================
The central operations desk:
- Command Metrics (Aspirants, Guides, SMEs, Journeys, Help Requests, Schemes)
- Guides Management & Account Provisioning (No public signup)
- SMEs Management & Account Provisioning (No public signup)
- Relationship Authority: Admin assigns Guide & SME to Aspirants
- Aspirants Directory & Drill-down (Full Profile, Relationships, Journey, Matches)
- Global Journey Timeline inspection with override management
- Help Requests Console (Ticket management & official responses)
- Scheme Catalogue CRUD (Add, Edit, Toggle Active/Archive)
"""

import streamlit as st
from datetime import datetime, timezone
from services.auth import admin_create_mentor
from services.local_db import get_local_db
from services.profiles import get_profile
from services.relationships import get_aspirant_mentors, assign_guide, assign_sme
from services.journey import get_journey_timeline, soft_delete_event, log_meaningful_event
from services.schemes import list_schemes, get_scheme, upsert_scheme, toggle_archive_scheme, delete_scheme, match_schemes_for_aspirant
from services.help_requests import list_requests, resolve_request

def render_admin_portal(admin_profile: dict):
    admin_id = admin_profile["id"]
    admin_name = admin_profile.get("full_name", "Administrator")
    local_db = get_local_db()

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #E2E8F0;">
        <div>
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#DB2777;">Admin Command Center</div>
            <h1 style="font-size:2rem; font-weight:800; margin:0; color:#0F172A;">FULCRUM-INDIA Control Tower</h1>
            <p style="font-size:0.95rem; color:#475569; margin-top:0.25rem;">
                Program Administration, Mentorship Governance & Scheme Intelligence
            </p>
        </div>
        <div style="text-align:right;">
            <span style="display:inline-block; padding:4px 14px; border-radius:12px; font-size:0.85rem; font-weight:700; background:#FDF2F8; color:#DB2777; border:1px solid #FBCFE8;">
                Admin: {admin_name}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch stats
    aspirants = local_db.list_profiles_by_role("aspirant")
    guides = local_db.list_profiles_by_role("guide")
    smes = local_db.list_profiles_by_role("sme")
    all_schemes = list_schemes(active_only=False)
    help_tickets = list_requests()
    open_tickets = [t for t in help_tickets if t.get("status") in ("OPEN", "IN_PROGRESS")]

    # 6 Top Metric Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #6366f1; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Aspirants</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(aspirants)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #10b981; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Active Guides</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(guides)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #f59e0b; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Active SMEs</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(smes)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #3b82f6; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Active Journeys</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(aspirants)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #ef4444; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Open Help</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(open_tickets)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-bottom:3px solid #ec4899; border-radius:12px; padding:0.9rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Schemes</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(all_schemes)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # Admin Tabs
    tabs = st.tabs([
        "👥 Aspirants & Journeys",
        "🧭 Guides Management",
        "🔬 SMEs Management",
        "🎯 Mentor Assignments",
        "💬 Help Requests Queue",
        "🏦 Scheme Catalogue (CRUD)"
    ])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: ASPIRANTS & JOURNEYS
    # ─────────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Entrepreneurs Directory")
        if not aspirants:
            st.info("No Aspirants have signed up yet.")
        else:
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                asp_options = {a["id"]: f"{a['full_name']} — {a.get('profile_data',{}).get('business',{}).get('business_name','Enterprise')} ({a.get('district','TN')})" for a in aspirants}
                selected_asp_id = st.selectbox("Select Entrepreneur to inspect", list(asp_options.keys()), format_func=lambda x: asp_options[x], key="adm_sel_asp")

            curr_asp = get_profile(selected_asp_id)
            if curr_asp:
                mentors_info = get_aspirant_mentors(selected_asp_id)
                g_assigned = mentors_info.get("guide")
                s_assigned = mentors_info.get("sme")
                b_info = curr_asp.get("profile_data", {}).get("business", {})

                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:1.25rem; margin:1rem 0; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; color:#0F172A;">{curr_asp['full_name']}</h3>
                            <div style="color:#2563EB; font-weight:600; margin-top:2px;">{b_info.get('business_name','Enterprise')} · {b_info.get('sector','General')} ({b_info.get('stage','idea')})</div>
                            <div style="color:#475569; font-size:0.85rem; margin-top:0.25rem;">Email: {curr_asp['email']} | Phone: {curr_asp.get('phone')} | District: {curr_asp.get('district')}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:0.9rem; color:#334155;"><strong style="color:#0F172A;">Guide:</strong> <span style="color:#059669; font-weight:700;">{g_assigned.get('full_name') if g_assigned else 'None'}</span></div>
                            <div style="font-size:0.9rem; color:#334155; margin-top:3px;"><strong style="color:#0F172A;">SME:</strong> <span style="color:#D97706; font-weight:700;">{s_assigned.get('full_name') if s_assigned else 'None'}</span></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### Complete Chronological Journey")
                timeline = get_journey_timeline(selected_asp_id)
                if not timeline:
                    st.info("No journey events recorded yet for this entrepreneur.")
                else:
                    for event in timeline:
                        actor_role = event.get("actor_role", "aspirant")
                        actor_name = event.get("actor_name") or "System"
                        ev_data = event.get("event_data", {})
                        title = ev_data.get("title") or event.get("event_type")
                        desc = ev_data.get("description", "")
                        date_display = str(event.get("event_date", ""))[:10]

                        badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                        col_t, col_b, col_ov = st.columns([1.2, 5, 0.8])
                        with col_t:
                            st.markdown(f"""
                            <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                            <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{actor_role}</span>
                            """, unsafe_allow_html=True)
                        with col_b:
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                <div style="font-weight:700; color:#0F172A; font-size:1.02rem;">{title}</div>
                                <div style="color:#334155; font-size:0.88rem; margin-top:0.25rem; line-height:1.4;">{desc}</div>
                                <div style="font-size:0.75rem; color:#64748B; margin-top:0.3rem;">Actor: {actor_name} ({actor_role})</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_ov:
                            # Admin override soft delete
                            if st.button("🗑️", key=f"adm_del_{event['id']}", help="Administrative removal (Soft Delete)"):
                                soft_delete_event(event["id"], admin_id, "admin")
                                st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB 2: GUIDES MANAGEMENT & PROVISIONING
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Guides Roster & Account Provisioning")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Guides can ONLY be created by the Admin. Public signup is disabled.</p>", unsafe_allow_html=True)

        with st.expander("➕ Provision New Guide Account", expanded=False):
            with st.form("form_create_guide"):
                col_cg1, col_cg2 = st.columns(2)
                with col_cg1:
                    cg_name = st.text_input("Full Name *", placeholder="e.g. Rajendran / Murugan S.")
                    cg_email = st.text_input("Email *", placeholder="e.g. rajendran@mentor.in")
                    cg_phone = st.text_input("Phone Number", placeholder="9876543211")
                with col_cg2:
                    cg_loc = st.selectbox("Location / District", ["Madurai", "Chennai", "Coimbatore", "Salem", "Trichy", "Other"], key="cg_loc")
                    cg_exp = st.text_input("Primary Expertise *", placeholder="e.g. PMEGP Loan Specialist, Banking, Food Processing")
                    cg_pwd = st.text_input("Temporary Password", value="Guide@123")
                cg_bio = st.text_area("Professional Background", placeholder="Retired Chief Manager with 30 years experience in MSME lending.")

                if st.form_submit_button("CREATE GUIDE ACCOUNT", type="primary"):
                    if cg_name and cg_email and cg_exp:
                        g_prof, err = admin_create_mentor(
                            admin_user_id=admin_id,
                            role="guide",
                            full_name=cg_name,
                            email=cg_email,
                            phone=cg_phone,
                            location=cg_loc,
                            expertise=cg_exp,
                            temp_password=cg_pwd,
                            bio=cg_bio
                        )
                        if g_prof:
                            st.success(f"Guide account '{cg_name}' created successfully! Credentials: {cg_email} / {cg_pwd}")
                            st.rerun()
                        else:
                            st.error(err or "Failed to create guide.")
                    else:
                        st.warning("Please fill in all required fields.")

        # Guides Table
        if not guides:
            st.info("No guides currently registered. Create one above.")
        else:
            for g in guides:
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:0 10px 10px 0; padding:1rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong style="color:#0F172A; font-size:1.05rem;">{g['full_name']}</strong>
                            <span style="color:#059669; font-weight:600; font-size:0.85rem; margin-left:0.5rem;">({g['district']})</span>
                            <div style="color:#475569; font-size:0.85rem; margin-top:0.2rem;">Expertise: {g.get('profile_data',{}).get('expertise')} | Email: {g['email']}</div>
                        </div>
                        <span style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; font-size:0.75rem; font-weight:800; padding:3px 10px; border-radius:8px;">ACTIVE GUIDE</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB 3: SMES MANAGEMENT & PROVISIONING
    # ─────────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Subject Matter Experts Roster")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>SMEs provide specialized technical, legal, and compliance support (GST, FSSAI, Patents, Legal).</p>", unsafe_allow_html=True)

        with st.expander("➕ Provision New SME Account", expanded=False):
            with st.form("form_create_sme"):
                col_cs1, col_cs2 = st.columns(2)
                with col_cs1:
                    cs_name = st.text_input("Full Name *", placeholder="e.g. Kumar / Priya R.")
                    cs_email = st.text_input("Email *", placeholder="e.g. kumar@sme.in")
                    cs_phone = st.text_input("Phone Number", placeholder="9876543212")
                with col_cs2:
                    cs_loc = st.selectbox("Location / District", ["Madurai", "Chennai", "Coimbatore", "Salem", "Trichy", "Other"], key="cs_loc")
                    cs_exp = st.text_input("Specialization Domain *", placeholder="e.g. GST Auditing, Taxation, Corporate Compliance")
                    cs_pwd = st.text_input("Temporary Password", value="Sme@123")
                cs_ind = st.text_input("Industry Specialization", placeholder="e.g. Food Processing, Export, Manufacturing")
                cs_bio = st.text_area("Professional Summary", placeholder="Chartered Accountant and GST consultant advising MSMEs for 15 years.")

                if st.form_submit_button("CREATE SME ACCOUNT", type="primary"):
                    if cs_name and cs_email and cs_exp:
                        s_prof, err = admin_create_mentor(
                            admin_user_id=admin_id,
                            role="sme",
                            full_name=cs_name,
                            email=cs_email,
                            phone=cs_phone,
                            location=cs_loc,
                            expertise=cs_exp,
                            temp_password=cs_pwd,
                            bio=cs_bio,
                            industry=cs_ind
                        )
                        if s_prof:
                            st.success(f"SME account '{cs_name}' created successfully! Credentials: {cs_email} / {cs_pwd}")
                            st.rerun()
                        else:
                            st.error(err or "Failed to create SME.")
                    else:
                        st.warning("Please fill in required fields.")

        # SMEs Table
        if not smes:
            st.info("No SMEs registered. Create one above.")
        else:
            for s in smes:
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:0 10px 10px 0; padding:1rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong style="color:#0F172A; font-size:1.05rem;">{s['full_name']}</strong>
                            <span style="color:#D97706; font-weight:600; font-size:0.85rem; margin-left:0.5rem;">({s['district']})</span>
                            <div style="color:#475569; font-size:0.85rem; margin-top:0.2rem;">Domain: {s.get('profile_data',{}).get('expertise')} | Email: {s['email']}</div>
                        </div>
                        <span style="background:#FFFBEB; color:#D97706; border:1px solid #FDE68A; font-size:0.75rem; font-weight:800; padding:3px 10px; border-radius:8px;">ACTIVE SME</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB 4: MENTOR ASSIGNMENTS (Admin Authority)
    # ─────────────────────────────────────────────────────────────
    with tabs[3]:
        st.subheader("🎯 Assign Mentors to Entrepreneurs")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>The Admin is the exclusive authority for pairing Aspirants with Guides and SMEs.</p>", unsafe_allow_html=True)

        if not aspirants:
            st.warning("No Aspirants available for assignment.")
            return

        asp_dict = {a["id"]: f"{a['full_name']} ({a.get('district','Madurai')})" for a in aspirants}
        guide_dict = {g["id"]: f"{g['full_name']} — {g.get('profile_data',{}).get('expertise','Guide')}" for g in guides}
        sme_dict = {s["id"]: f"{s['full_name']} — {s.get('profile_data',{}).get('expertise','SME')}" for s in smes}

        col_as1, col_as2 = st.columns(2)

        with col_as1:
            st.markdown("#### Assign Dedicated Guide")
            with st.form("form_assign_guide"):
                sel_asp_for_g = st.selectbox("Select Aspirant", list(asp_dict.keys()), format_func=lambda x: asp_dict[x], key="asg_asp_g")
                if guide_dict:
                    sel_g = st.selectbox("Select Guide", list(guide_dict.keys()), format_func=lambda x: guide_dict[x], key="asg_guide")
                else:
                    st.warning("No Guides available. Please create a Guide first.")
                    sel_g = None
                g_notes = st.text_input("Mentorship Directive Notes", placeholder="e.g. Focus on PMEGP loan application & pricing")

                if st.form_submit_button("ASSIGN GUIDE", type="primary"):
                    if sel_asp_for_g and sel_g:
                        ok, err = assign_guide(sel_asp_for_g, sel_g, admin_id, g_notes)
                        if ok:
                            st.success(f"Assigned {guide_dict[sel_g]} to {asp_dict[sel_asp_for_g]}! Journey event logged.")
                            st.rerun()
                        else:
                            st.error(err or "Assignment failed.")

        with col_as2:
            st.markdown("#### Assign Specialized Domain SME")
            with st.form("form_assign_sme"):
                sel_asp_for_s = st.selectbox("Select Aspirant", list(asp_dict.keys()), format_func=lambda x: asp_dict[x], key="asg_asp_s")
                if sme_dict:
                    sel_s = st.selectbox("Select SME", list(sme_dict.keys()), format_func=lambda x: sme_dict[x], key="asg_sme")
                else:
                    st.warning("No SMEs available. Please create an SME first.")
                    sel_s = None
                s_notes = st.text_input("Specialist Task Notes", placeholder="e.g. Verify GST threshold and draft audit memorandum")

                if st.form_submit_button("ASSIGN SME", type="primary"):
                    if sel_asp_for_s and sel_s:
                        ok, err = assign_sme(sel_asp_for_s, sel_s, admin_id, s_notes)
                        if ok:
                            st.success(f"Assigned {sme_dict[sel_s]} to {asp_dict[sel_asp_for_s]}! Journey event logged.")
                            st.rerun()
                        else:
                            st.error(err or "Assignment failed.")

    # ─────────────────────────────────────────────────────────────
    # TAB 5: HELP REQUESTS QUEUE
    # ─────────────────────────────────────────────────────────────
    with tabs[4]:
        st.subheader("Support & Help Requests Queue")
        if not help_tickets:
            st.info("No help requests currently logged in system.")
        else:
            for ticket in help_tickets:
                t_id = ticket["id"]
                t_status = ticket.get("status", "OPEN")
                st_color = "#f59e0b" if t_status == "OPEN" else "#3b82f6" if t_status == "IN_PROGRESS" else "#10b981"

                with st.expander(f"[{t_status}] {ticket.get('aspirant_name', 'Founder')}: {ticket.get('subject')} (Priority: {ticket.get('priority', 'MEDIUM')})"):
                    st.markdown(f"""
                    <div style="font-size:0.95rem; color:#0F172A; margin-bottom:0.75rem;">
                        <strong>Message:</strong> {ticket.get('message')}
                    </div>
                    <div style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">
                        Founder Email: {ticket.get('aspirant_email')} | Submitted: {str(ticket.get('created_at',''))[:19]}
                    </div>
                    """, unsafe_allow_html=True)

                    with st.form(f"form_resp_{t_id}"):
                        c_st1, c_st2 = st.columns([1, 3])
                        with c_st1:
                            new_st = st.selectbox("Update Status", ["OPEN", "IN_PROGRESS", "RESOLVED"], index=["OPEN", "IN_PROGRESS", "RESOLVED"].index(t_status))
                        with c_st2:
                            resp_text = st.text_input("Admin Response", value=ticket.get("admin_response") or "Reviewed. Assigned guidance specialist.")

                        if st.form_submit_button("SUBMIT RESPONSE & UPDATE", type="primary"):
                            ok, err = resolve_request(t_id, new_st, resp_text, admin_id)
                            if ok:
                                st.success(f"Ticket updated to {new_st}!")
                                st.rerun()
                            else:
                                st.error(err or "Failed to update ticket.")

    # ─────────────────────────────────────────────────────────────
    # TAB 6: SCHEME CATALOGUE CRUD
    # ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────
    # TAB 6: SCHEME CATALOGUE CRUD
    # ─────────────────────────────────────────────────────────────
    with tabs[5]:
        st.subheader("Scheme Catalogue Management (170 Records in Intelligence Database)")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Full Administrative Authority: Search, filter, add new schemes, edit existing guidelines, toggle archive status, or permanently delete schemes from both local and cloud databases.</p>", unsafe_allow_html=True)

        # ── 1. ADD NEW SCHEME EXPANDER ──
        with st.expander("➕ Add New Scheme to Catalogue", expanded=False):
            with st.form("form_add_new_scheme"):
                c_ns1, c_ns2 = st.columns(2)
                with c_ns1:
                    ns_name = st.text_input("Scheme Name *", placeholder="e.g. IndiaAI Mission Compute & Startup Support")
                    ns_agency = st.text_input("Agency / Ministry *", placeholder="e.g. MeitY (Ministry of Electronics and IT)")
                    ns_amount = st.text_input("Funding Amount *", placeholder="e.g. Up to 40% compute GPU subsidy + Rs 1 Crore grant")
                    ns_type = st.selectbox("Funding Type", ["Grant", "Equity", "Subsidy", "Loan", "Credit Guarantee", "Compute GPU Subsidy & Cohort Grant", "Reimbursement Grant & Equity"])
                with c_ns2:
                    ns_cat = st.selectbox("Category", ["Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"])
                    ns_stage = st.selectbox("Eligible Stage", ["Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"])
                    ns_scope = st.selectbox("State Scope", ["All India", "Tamil Nadu", "Regional / Global"])
                    ns_url = st.text_input("Official Portal URL", placeholder="https://indiaai.gov.in")

                ns_brief = st.text_input("One-line Brief", placeholder="Compute infrastructure subsidies and equity/grant support for AI startups.")
                ns_desc = st.text_area("Full Description / Scope", placeholder="Access to 10,000+ GPUs onboarded via empaneled providers plus cohort grants for AI ventures.")

                if st.form_submit_button("ADD SCHEME TO CATALOGUE", type="primary"):
                    if ns_name and ns_agency:
                        import uuid
                        new_s_obj = {
                            "id": f"SCH-ADMIN-{uuid.uuid4().hex[:8].upper()}",
                            "name": ns_name,
                            "agency": ns_agency,
                            "category_type": ns_cat,
                            "funding_type": ns_type,
                            "stage": ns_stage,
                            "amount": ns_amount,
                            "brief": ns_brief or ns_name,
                            "description": ns_desc or ns_brief or ns_name,
                            "sectors": ["General", "DeepTech", "AI"],
                            "state_scope": ns_scope,
                            "application_url": ns_url,
                            "is_active": True,
                            "status": "active",
                            "source_dataset": "Manual Admin Addition"
                        }
                        ok, err = upsert_scheme(new_s_obj, admin_id)
                        if ok:
                            st.success(f"Added '{ns_name}' to catalogue!")
                            st.rerun()
                        else:
                            st.error(err or "Failed to add scheme.")
                    else:
                        st.warning("Scheme Name and Agency are required.")

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # ── 2. SEARCH & MULTI-FACET FILTERS ──
        c_f1, c_f2, c_f3, c_f4 = st.columns([2.5, 1.2, 1.2, 1.1])
        with c_f1:
            sc_search = st.text_input("🔍 Search Funds & Schemes", placeholder="Search by name, agency, keyword (e.g. IndiaAI, DLI, Accel, NEEDS, PMEGP, TANSEED)...", key="adm_sc_search")
        with c_f2:
            sc_cat = st.selectbox("Category", ["ALL", "Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"], key="adm_sc_cat")
        with c_f3:
            sc_stage = st.selectbox("Stage", ["ALL", "Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"], key="adm_sc_stage")
        with c_f4:
            sc_status = st.selectbox("Status", ["ALL", "Active Only", "Archived Only"], key="adm_sc_status")

        active_filter = None if sc_status == "ALL" else True if sc_status == "Active Only" else False
        all_matches = list_schemes(search=sc_search, category=sc_cat, stage=sc_stage, active_only=False)

        if active_filter is not None:
            all_matches = [s for s in all_matches if s.get("is_active", True) == active_filter]

        total_count = len(all_matches)

        # ── 3. PAGINATION & PAGE SIZE ──
        c_bar1, c_bar2 = st.columns([2.5, 1.5])
        with c_bar1:
            st.markdown(f"**Found {total_count} schemes matching filter.**")
        with c_bar2:
            page_size_option = st.selectbox("Schemes per page", [15, 30, 50, 100, "All (170)"], index=1, key="adm_page_size")

        if page_size_option == "All (170)":
            page_size = total_count if total_count > 0 else 1
        else:
            page_size = int(page_size_option)

        import math
        total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1

        if "adm_scheme_page" not in st.session_state:
            st.session_state.adm_scheme_page = 1
        if st.session_state.adm_scheme_page > total_pages:
            st.session_state.adm_scheme_page = 1

        c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
        with c_p1:
            if st.button("◀ Previous Page", disabled=(st.session_state.adm_scheme_page <= 1), use_container_width=True):
                st.session_state.adm_scheme_page -= 1
                st.rerun()
        with c_p2:
            st.markdown(f"<div style='text-align:center; padding-top:6px; font-weight:600; color:#475569;'>Page {st.session_state.adm_scheme_page} of {total_pages} ({total_count} Total Schemes)</div>", unsafe_allow_html=True)
        with c_p3:
            if st.button("Next Page ▶", disabled=(st.session_state.adm_scheme_page >= total_pages), use_container_width=True):
                st.session_state.adm_scheme_page += 1
                st.rerun()

        start_idx = (st.session_state.adm_scheme_page - 1) * page_size
        end_idx = start_idx + page_size
        page_schemes = all_matches[start_idx:end_idx]

        if not page_schemes:
            st.info("No schemes match your search criteria. Try clearing search keywords or resetting filters.")
        else:
            # ── 4. RICH SCHEME CARDS WITH FULL EDIT & DELETE ──
            for s in page_schemes:
                is_active = s.get("is_active", True)
                status_tag = "ACTIVE" if is_active else "ARCHIVED"
                status_bg = "#ECFDF5" if is_active else "#F1F5F9"
                status_fg = "#059669" if is_active else "#64748B"
                status_border = "#A7F3D0" if is_active else "#CBD5E1"

                cat_tag = s.get("category_type", "Govt")
                cat_bg = "#EFF6FF" if "Central" in cat_tag else "#F5F3FF" if "State" in cat_tag else "#FDF2F8"
                cat_fg = "#2563EB" if "Central" in cat_tag else "#7C3AED" if "State" in cat_tag else "#DB2777"

                funding_type = s.get("funding_type") or "Grant / Support"
                stage_tag = s.get("stage") or "All Stages"
                amount_str = s.get("amount") or "Guidelines specified"
                scope_str = s.get("state_scope") or "All India"

                # Container Card
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.4rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                        <div style="flex:1; min-width:280px;">
                            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                                <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:{cat_bg}; color:{cat_fg};">{cat_tag}</span>
                                <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:#F8FAFC; color:#475569; border:1px solid #E2E8F0;">{funding_type}</span>
                                <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:#F8FAFC; color:#475569; border:1px solid #E2E8F0;">{stage_tag}</span>
                                <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:{status_bg}; color:{status_fg}; border:1px solid {status_border};">{status_tag}</span>
                            </div>
                            <div style="font-size:1.15rem; font-weight:800; color:#0F172A; line-height:1.3;">{s['name']}</div>
                            <div style="font-size:0.85rem; color:#64748B; font-weight:600; margin-top:3px;">
                                Agency / Institution: <span style="color:#334155;">{s.get('agency') or 'Central / State Ministry'}</span>
                            </div>
                        </div>
                    </div>
                    <div style="color:#059669; font-weight:700; font-size:0.95rem; margin:0.5rem 0 0.4rem;">
                        💵 Funding Amount: {amount_str}
                    </div>
                    <div style="color:#334155; font-size:0.88rem; line-height:1.45; margin-bottom:0.6rem;">
                        {s.get('brief') or s.get('description') or 'Comprehensive capital support and mentorship.'}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:#64748B; padding-top:0.4rem; border-top:1px solid #F1F5F9;">
                        <div>📍 Geography / Scope: <strong>{scope_str}</strong></div>
                        <div>{f'<a href="{s["application_url"]}" target="_blank" style="color:#2563EB; font-weight:600; text-decoration:none;">Official Portal Link ↗</a>' if s.get("application_url") else ''}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Action Controls Row: Edit, Archive, Delete
                c_act1, c_act2, c_act3 = st.columns([2, 1, 1])

                with c_act1:
                    with st.expander(f"✏️ Edit '{s['name']}' Details"):
                        with st.form(f"form_edit_sc_{s['id']}"):
                            c_es1, c_es2 = st.columns(2)
                            with c_es1:
                                ed_name = st.text_input("Scheme Name", value=s["name"])
                                ed_agency = st.text_input("Agency / Ministry", value=s.get("agency", ""))
                                ed_amount = st.text_input("Funding Amount", value=s.get("amount", ""))
                                ed_type = st.text_input("Funding Type", value=s.get("funding_type", "Grant"))
                            with c_es2:
                                ed_url = st.text_input("Application URL", value=s.get("application_url", ""))
                                ed_cat = st.selectbox("Category", ["Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"], index=0 if "Central" in s.get("category_type","") else 1 if "State" in s.get("category_type","") else 2 if "Private" in s.get("category_type","") else 3)
                                ed_stage = st.selectbox("Stage", ["Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"], index=0 if s.get("stage") == "Ideation / R&D" else 1 if s.get("stage") == "Pre-Seed / Seed" else 2 if s.get("stage") == "Pre-Series A / Series A" else 3)
                                ed_scope = st.selectbox("Scope", ["All India", "Tamil Nadu", "Regional / Global"], index=0 if s.get("state_scope") == "All India" else 1)

                            ed_brief = st.text_input("One-line Brief", value=s.get("brief", ""))
                            ed_desc = st.text_area("Full Description", value=s.get("description", ""))

                            if st.form_submit_button("SAVE UPDATES", type="primary"):
                                s["name"] = ed_name
                                s["agency"] = ed_agency
                                s["amount"] = ed_amount
                                s["funding_type"] = ed_type
                                s["category_type"] = ed_cat
                                s["application_url"] = ed_url
                                s["stage"] = ed_stage
                                s["state_scope"] = ed_scope
                                s["brief"] = ed_brief
                                s["description"] = ed_desc
                                upsert_scheme(s, admin_id)
                                st.success(f"Updated '{ed_name}'!")
                                st.rerun()

                with c_act2:
                    action_name = "📦 Archive Scheme" if is_active else "🚀 Activate Scheme"
                    if st.button(action_name, key=f"btn_arch_{s['id']}", use_container_width=True):
                        toggle_archive_scheme(s["id"], admin_id)
                        st.success(f"Changed status to {'Archived' if is_active else 'Active'}!")
                        st.rerun()

                with c_act3:
                    if st.button("🗑️ Delete Scheme", key=f"btn_del_{s['id']}", help="Permanently delete from database", use_container_width=True):
                        st.session_state[f"confirm_delete_{s['id']}"] = True

                    if st.session_state.get(f"confirm_delete_{s['id']}"):
                        st.warning(f"Permanently delete '{s['name']}'?")
                        c_cd1, c_cd2 = st.columns(2)
                        with c_cd1:
                            if st.button("CONFIRM DELETE", key=f"btn_cd_yes_{s['id']}", type="primary"):
                                delete_scheme(s["id"], admin_id)
                                st.session_state.pop(f"confirm_delete_{s['id']}", None)
                                st.success(f"Permanently deleted '{s['name']}' from catalogue!")
                                st.rerun()
                        with c_cd2:
                            if st.button("CANCEL", key=f"btn_cd_no_{s['id']}"):
                                st.session_state.pop(f"confirm_delete_{s['id']}", None)
                                st.rerun()
