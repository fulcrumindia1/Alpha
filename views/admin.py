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
import html
from datetime import datetime, timezone

def _safe_esc(val, default=""):
    """Crash-proof HTML escape that safely handles None, booleans, and non-string types."""
    if val is None:
        return default
    return html.escape(str(val))
from services.auth import admin_create_mentor, backfill_auth_users, get_data_backend
from services.profiles import get_profile, list_profiles_by_role
from services.relationships import get_aspirant_mentors, assign_guide, assign_sme
from services.journey import get_journey_timeline, soft_delete_event, log_meaningful_event, add_admin_journey_entry, get_standard_role_label
from services.schemes import list_schemes, get_scheme, upsert_scheme, toggle_archive_scheme, delete_scheme, match_schemes_for_aspirant
from services.pdf_generator import generate_aspirant_dossier_pdf
from services.schemes_ui import render_fund_explorer_card
from services.help_requests import list_mentor_admin_queries, admin_respond_to_mentor
from services.constants import (
    MASTER_SECTORS,
    MASTER_STAGES,
    MASTER_DISTRICTS_TN,
    MASTER_FUNDING_TYPES,
    MASTER_CATEGORY_TYPES,
    MASTER_GEOGRAPHIC_SCOPES
)

def render_admin_portal(admin_profile: dict):
    admin_id = admin_profile["id"]
    admin_name = admin_profile.get("full_name", "Administrator")

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

    # In Supabase mode, allow Admin to run safe backfill/sync
    if get_data_backend() == "supabase":
        with st.expander("⚡ Supabase Auth Synchronization & User Backfill", expanded=False):
            st.markdown("<p style='font-size:0.85rem; color:#64748B;'>Sync registered Supabase Auth users to application profiles, journeys, and mentor relationship records.</p>", unsafe_allow_html=True)
            col_bf1, col_bf2 = st.columns([2, 1])
            with col_bf1:
                admin_email_to_promote = st.text_input("Designated Super Admin Email", value="admin@fulcrum.in", key="admin_sync_email")
            with col_bf2:
                st.write("")
                st.write("")
                if st.button("🔄 Sync Auth Users", key="btn_admin_sync_auth"):
                    bf_res = backfill_auth_users(default_admin_email=admin_email_to_promote)
                    if "error" in bf_res:
                        st.error(bf_res["error"])
                    else:
                        st.success(f"Sync complete: {bf_res.get('backfilled', 0)} backfilled, {bf_res.get('already_existing', 0)} verified (Total Auth Users: {bf_res.get('total_auth_users', 0)}).")
                        st.rerun()

    # Fetch stats
    aspirants = list_profiles_by_role("aspirant")
    guides = list_profiles_by_role("guide")
    smes = list_profiles_by_role("sme")
    all_schemes = list_schemes(active_only=False)
    mentor_queries = list_mentor_admin_queries()
    pending_directives = [q for q in mentor_queries if q.get("status") == "PENDING_ADMIN"]

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
            <div style="font-size:0.72rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px;">Directives Needed</div>
            <div style="font-size:1.75rem; font-weight:800; color:#0F172A; margin-top:2px;">{len(pending_directives)}</div>
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
        "🏛️ Mentor Inquiries & Directives",
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
            with col_sel2:
                st.markdown("<div style='height: 1.75rem;'></div>", unsafe_allow_html=True)

            curr_asp = get_profile(selected_asp_id)
            if curr_asp:
                with col_sel2:
                    try:
                        cached_bytes = st.session_state.get("cached_dossier_pdf")
                        if (
                            st.session_state.get("cached_dossier_asp_id") != selected_asp_id 
                            or not cached_bytes 
                            or len(cached_bytes) < 1000
                        ):
                            with st.spinner("Compiling Dossier PDF..."):
                                st.session_state["cached_dossier_pdf"] = generate_aspirant_dossier_pdf(selected_asp_id)
                                st.session_state["cached_dossier_asp_id"] = selected_asp_id
                        pdf_data = st.session_state["cached_dossier_pdf"]
                        clean_name = "".join(c for c in curr_asp.get("full_name", "Aspirant") if c.isalnum() or c == "_")
                        st.download_button(
                            label="📥 Download Founder Dossier (PDF)",
                            data=pdf_data,
                            file_name=f"FULCRUM_Dossier_{clean_name}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"dl_pdf_dossier_{selected_asp_id}"
                        )
                    except Exception as e:
                        st.error(f"PDF generation error: {e}")
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

                with st.expander(f"➕ Log Official Administrative Directive to {curr_asp['full_name']}'s Journey", expanded=False):
                    if "admin_directive_success" in st.session_state:
                        _ad_msg = st.session_state.pop("admin_directive_success")
                        st.success(_ad_msg)
                        try:
                            st.toast(_ad_msg, icon="✅")
                        except Exception:
                            pass
                    with st.form(f"form_admin_add_journey_{selected_asp_id}"):
                        c_ad1, c_ad2 = st.columns(2)
                        with c_ad1:
                            ad_title = st.text_input("Title / Directive Milestone *", placeholder="e.g. Subsidy Sanction Review & Allocation Approval")
                            ad_cat = st.selectbox("Directive Category", ["Official Sanction", "Administrative Review", "Compliance Clearance", "Grant Allocation", "Program Onboarding", "Other / Custom Directive"])
                        with c_ad2:
                            ad_date = st.date_input("Directive Date", value=datetime.now(timezone.utc).date())
                        ad_desc = st.text_area("Administrative Notes / Directive Details *", placeholder="Formally reviewed founder's DPR and cap table. Cleared for departmental tranche disbursement.")
                        if st.form_submit_button("RECORD ADMINISTRATIVE DIRECTIVE", type="primary"):
                            if ad_title and ad_desc:
                                ev, err = add_admin_journey_entry(
                                    aspirant_id=selected_asp_id,
                                    admin_id=admin_id,
                                    title=ad_title,
                                    description=ad_desc,
                                    category=ad_cat,
                                    event_date=ad_date.isoformat()
                                )
                                if ev:
                                    st.session_state.pop("cached_dossier_pdf", None)
                                    st.session_state["admin_directive_success"] = f"Administrative directive '{ad_title}' recorded to {curr_asp['full_name']}'s Journey!"
                                    st.rerun()
                                else:
                                    st.error(err or "Failed to record directive.")
                            else:
                                st.warning("Please provide both title and description.")

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
                    st.info("No journey events recorded yet for this entrepreneur.")
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
                                actor_name = "System"
                        std_role = get_standard_role_label(actor_role)
                        ev_data = event.get("event_data", {})
                        raw_title = ev_data.get("title") or event.get("event_type") or "Milestone"
                        raw_desc = ev_data.get("description", "")
                        title = _safe_esc(raw_title, default="Milestone")
                        desc = _safe_esc(raw_desc, default="").replace("\n", "<br>")
                        date_display = str(event.get("event_date", ""))[:10]

                        badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                        inc = event.get("included_in_roadmap", True)
                        if inc is False:
                            status_badge_html = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:2px 8px; border-radius:6px; margin-left:8px;">⚠️ Marked \'Not Needed\' by Aspirant</span>'
                        else:
                            status_badge_html = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; padding:2px 8px; border-radius:6px; margin-left:8px;">✓ Active on Aspirant Roadmap</span>'

                        col_t, col_b, col_ov = st.columns([1.2, 5, 0.8])
                        with col_t:
                            st.markdown(f"""
                            <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                            <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{std_role}</span>
                            """, unsafe_allow_html=True)
                        with col_b:
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                    <div style="font-weight:700; color:#0F172A; font-size:1.02rem;">{title}</div>
                                    <div>{status_badge_html}</div>
                                </div>
                                <div style="color:#334155; font-size:0.88rem; margin-top:0.25rem; line-height:1.4;">{desc}</div>
                                <div style="font-size:0.75rem; color:#64748B; margin-top:0.3rem;">Contributor: <strong>{actor_name}</strong> ({std_role})</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_ov:
                            # Admin override soft delete
                            if st.button("🗑️", key=f"adm_del_{event['id']}", help="Administrative removal (Soft Delete)"):
                                ok, err = soft_delete_event(event["id"], admin_id, "admin")
                                if ok:
                                    st.session_state["del_event_success"] = "Journey entry removed."
                                else:
                                    st.session_state["del_event_err"] = err or "Could not remove entry."
                                st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB 2: GUIDES MANAGEMENT & PROVISIONING
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Guides Roster & Account Provisioning")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Guides can ONLY be created by the Admin. Public signup is disabled.</p>", unsafe_allow_html=True)

        with st.expander("➕ Provision New Guide Account", expanded=False):
            if "admin_guide_create_success" in st.session_state:
                _gc_msg = st.session_state.pop("admin_guide_create_success")
                st.success(_gc_msg)
                try:
                    st.toast(_gc_msg, icon="✅")
                except Exception:
                    pass
            with st.form("form_create_guide"):
                col_cg1, col_cg2 = st.columns(2)
                with col_cg1:
                    cg_name = st.text_input("Full Name *", placeholder="e.g. Rajendran / Murugan S.")
                    cg_email = st.text_input("Email *", placeholder="e.g. rajendran@mentor.in")
                    cg_phone = st.text_input("Phone Number", placeholder="9876543211")
                with col_cg2:
                    cg_loc_sel = st.selectbox("Location / District", MASTER_DISTRICTS_TN, index=13, key="cg_loc")
                    cg_loc = cg_loc_sel
                    if cg_loc_sel == "Other District / Non-TN (Specify)":
                        cg_loc_custom = st.text_input("Specify Location / State *", placeholder="e.g. Bengaluru (Karnataka)", key="cg_custom_loc")
                        if cg_loc_custom and cg_loc_custom.strip():
                            cg_loc = cg_loc_custom.strip()
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
                            st.session_state["admin_guide_create_success"] = f"✅ Guide account '{cg_name}' created successfully! Credentials: {cg_email} / {cg_pwd}"
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
            if "admin_sme_create_success" in st.session_state:
                _sc_msg = st.session_state.pop("admin_sme_create_success")
                st.success(_sc_msg)
                try:
                    st.toast(_sc_msg, icon="✅")
                except Exception:
                    pass
            with st.form("form_create_sme"):
                col_cs1, col_cs2 = st.columns(2)
                with col_cs1:
                    cs_name = st.text_input("Full Name *", placeholder="e.g. Kumar / Priya R.")
                    cs_email = st.text_input("Email *", placeholder="e.g. kumar@sme.in")
                    cs_phone = st.text_input("Phone Number", placeholder="9876543212")
                with col_cs2:
                    cs_loc_sel = st.selectbox("Location / District", MASTER_DISTRICTS_TN, index=13, key="cs_loc")
                    cs_loc = cs_loc_sel
                    if cs_loc_sel == "Other District / Non-TN (Specify)":
                        cs_loc_custom = st.text_input("Specify Location / State *", placeholder="e.g. Mumbai (Maharashtra)", key="cs_custom_loc")
                        if cs_loc_custom and cs_loc_custom.strip():
                            cs_loc = cs_loc_custom.strip()
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
                            st.session_state["admin_sme_create_success"] = f"✅ SME account '{cs_name}' created successfully! Credentials: {cs_email} / {cs_pwd}"
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
            if "assign_guide_success" in st.session_state:
                _g_msg = st.session_state.pop("assign_guide_success")
                st.success(_g_msg)
                try:
                    st.toast(_g_msg, icon="✅")
                except Exception:
                    pass
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
                            st.session_state["assign_guide_success"] = f"✅ Guide Assigned: {guide_dict[sel_g]} has been assigned to {asp_dict[sel_asp_for_g]}! Journey event logged."
                            st.rerun()
                        else:
                            st.error(err or "Assignment failed.")

        with col_as2:
            st.markdown("#### Assign Specialized Domain SME")
            if "assign_sme_success" in st.session_state:
                _s_msg = st.session_state.pop("assign_sme_success")
                st.success(_s_msg)
                try:
                    st.toast(_s_msg, icon="✅")
                except Exception:
                    pass
            with st.form("form_assign_sme"):
                sel_asp_for_s = st.selectbox("Select Aspirant", list(asp_dict.keys()), format_func=lambda x: asp_dict[x], key="asg_asp_s")
                if sme_dict:
                    sel_s = st.selectbox("Select SME", list(sme_dict.keys()), format_func=lambda x: sme_dict[x], key="asg_sme")
                else:
                    st.warning("No SMEs available. Please create an SME first.")
                    sel_s = None
                sme_asg_mode = st.radio(
                    "Assignment Mode",
                    options=["➕ Add Specialist to Advisory Panel (Concurrent Multi-SME)", "🔄 Replace Existing Specialist"],
                    index=0,
                    help="Choose whether to add this SME alongside other specialists (e.g., GST + Legal + FSSAI) or replace the existing specialist."
                )
                s_notes = st.text_input("Specialist Task Notes", placeholder="e.g. Verify GST threshold and draft audit memorandum")

                if st.form_submit_button("ASSIGN SME", type="primary"):
                    if sel_asp_for_s and sel_s:
                        mode = "add" if "Add" in sme_asg_mode else "replace"
                        ok, err = assign_sme(sel_asp_for_s, sel_s, admin_id, s_notes, mode=mode)
                        if ok:
                            action_desc = "added to advisory panel of" if mode == "add" else "assigned to"
                            st.session_state["assign_sme_success"] = f"✅ SME Assigned: Specialist {sme_dict[sel_s]} {action_desc} {asp_dict[sel_asp_for_s]}! Journey event logged."
                            st.rerun()
                        else:
                            st.error(err or "Assignment failed.")

    # ─────────────────────────────────────────────────────────────
    # TAB 5: MENTOR INQUIRIES & ADMINISTRATIVE DIRECTIVES
    # ─────────────────────────────────────────────────────────────
    with tabs[4]:
        st.subheader("🏛️ Mentor Inquiries & Administrative Directives")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Official Program Directorate Governance: Guides and Domain SMEs submit institutional roadblocks on behalf of their assigned entrepreneurs. Review inquiries, issue binding Administrative Directives, or assign Co-Guides (Guide B) and specialized Domain SMEs. <em>(Strictly invisible to the entrepreneur)</em></p>", unsafe_allow_html=True)

        col_mq1, col_mq2 = st.columns([2, 2])
        with col_mq1:
            st_filter = st.selectbox("Directive Status Filter", ["ALL", "PENDING_ADMIN", "DIRECTIVE_ISSUED", "RESOLVED"], key="admin_dir_st_filter")
        with col_mq2:
            role_filter = st.selectbox("Mentor Role Filter", ["ALL", "guide", "sme"], format_func=lambda x: "All Roles" if x == "ALL" else ("Guides Only" if x == "guide" else "Domain SMEs Only"), key="admin_dir_role_filter")

        all_queries = list_mentor_admin_queries()
        if st_filter != "ALL":
            all_queries = [q for q in all_queries if q.get("status") == st_filter]
        if role_filter != "ALL":
            all_queries = [q for q in all_queries if (q.get("requester_role_actual") or q.get("requester_role")) == role_filter]

        if not all_queries:
            st.info("No mentor administrative inquiries currently recorded matching the filter criteria.")
        else:
            # Build Guide and SME lookup dictionaries for co-assignment options
            guides_list = list_profiles_by_role("guide")
            smes_list = list_profiles_by_role("sme")
            guide_options = {"NONE": "None (Keep Current Mentorship Team)"}
            for g in guides_list:
                guide_options[g["id"]] = f"{g['full_name']} ({g.get('district', 'Tamil Nadu')})"
            sme_options = {"NONE": "None (No Additional Domain SME)"}
            for s in smes_list:
                sme_options[s["id"]] = f"{s['full_name']} — {s.get('profile_data',{}).get('expertise', 'Specialist')}"

            for query in all_queries:
                q_id = query["id"]
                q_status = query.get("status", "PENDING_ADMIN")
                st_color = "#f59e0b" if q_status == "PENDING_ADMIN" else "#10b981"
                mentor_role_lbl = (query.get("requester_role_actual") or query.get("requester_role") or "guide").upper()
                mentor_name = query.get("requester_name") or "Mentor"
                asp_name = query.get("aspirant_name") or "Entrepreneur"
                q_sub = _safe_esc(query.get("subject"), default="Institutional Query")
                q_priority = query.get("priority", "MEDIUM")

                with st.expander(f"[{q_status}] For Mentee: {asp_name} | From {mentor_role_lbl}: {mentor_name} — {q_sub} ({q_priority})", expanded=(q_status == "PENDING_ADMIN")):
                    q_card_html = (
                        f'<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid {st_color}; border-radius:0 8px 8px 0; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">'
                        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                        f'<div style="font-weight:800; color:#0F172A; font-size:1.05rem;">{q_sub}</div>'
                        f'<div style="font-size:0.8rem; color:#64748B;">Submitted: {str(query.get("created_at",""))[:16]}</div>'
                        f'</div>'
                        f'<div style="font-size:0.85rem; color:#475569; margin:4px 0;">'
                        f'Submitted by: <strong>{mentor_name}</strong> ({mentor_role_lbl}) on behalf of entrepreneur: <strong style="color:#0F172A;">{asp_name}</strong>'
                        f'</div>'
                        f'<div style="font-size:0.92rem; color:#1E293B; margin-top:0.5rem; line-height:1.5;">'
                        f'{_safe_esc(query.get("message"), default="").replace(chr(10), "<br>")}'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(q_card_html, unsafe_allow_html=True)

                    if query.get("admin_directive"):
                        ad_msg = _safe_esc(query.get("admin_directive"), default="").replace(chr(10), "<br>")
                        ad_issued = str(query.get("directive_issued_at", ""))[:16]
                        dir_card_html = (
                            f'<div style="background:#F0FDF4; border:1px solid #86EFAC; border-left:4px solid #16A34A; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-bottom:0.75rem;">'
                            f'<div style="font-weight:800; color:#15803D; font-size:0.88rem; display:flex; justify-content:space-between;">'
                            f'<span>🏛️ Issued Directorate Directive</span>'
                            f'<span style="font-size:0.75rem; color:#166534; font-weight:600;">Issued: {ad_issued}</span>'
                            f'</div>'
                            f'<div style="font-size:0.9rem; color:#14532D; margin-top:0.35rem; line-height:1.5;">'
                            f'{ad_msg}'
                            f'</div>'
                            f'</div>'
                        )
                        st.markdown(dir_card_html, unsafe_allow_html=True)

                    if f"admin_inquiry_directive_success_{q_id}" in st.session_state:
                        _dq_msg = st.session_state.pop(f"admin_inquiry_directive_success_{q_id}")
                        st.success(_dq_msg)
                        try:
                            st.toast(_dq_msg, icon="✅")
                        except Exception:
                            pass

                    with st.form(f"form_admin_dir_{q_id}"):
                        st.markdown("##### 🏛️ Issue Official Administrative Directive")
                        st.caption("The directive will be dispatched directly to the mentor. The entrepreneur will never see this administrative communication.")

                        col_d1, col_d2 = st.columns([1, 2])
                        with col_d1:
                            status_choices = ["DIRECTIVE_ISSUED", "RESOLVED", "PENDING_ADMIN"]
                            cur_st_idx = status_choices.index(q_status) if q_status in status_choices else 0
                            new_st = st.selectbox("Directive Status", status_choices, index=cur_st_idx, key=f"dir_st_{q_id}")
                        with col_d2:
                            directive_text = st.text_area("Administrative Directive / Resolution Instructions *", value=query.get("admin_directive") or "", placeholder="e.g. Approved DIC fast-track liaison. Authorized subsidy exception. Assigned Co-Guide B to oversee bank sanction documents. Guide to communicate milestones to founder.", height=80, key=f"dir_txt_{q_id}")

                        st.markdown("###### 🤝 Operational Support Options (Assign on Behalf of Mentee)")
                        col_asg1, col_asg2 = st.columns(2)
                        with col_asg1:
                            sel_co_guide = st.selectbox("Assign / Consult Co-Guide (Guide B)", list(guide_options.keys()), format_func=lambda x: guide_options[x], key=f"dir_cog_{q_id}", help="Adds an additional Guide to the entrepreneur's roster (as Guide B) without removing primary Guide A.")
                        with col_asg2:
                            sel_add_sme = st.selectbox("Assign / Add Domain Specialist (SME)", list(sme_options.keys()), format_func=lambda x: sme_options[x], key=f"dir_sme_{q_id}", help="Adds a domain specialist (GST, Legal, FSSAI, Patents) to the entrepreneur's advisory panel.")

                        if st.form_submit_button("ISSUE DIRECTIVE & UPDATE", type="primary"):
                            if not directive_text.strip():
                                st.warning("Please enter the directive instructions for the mentor.")
                            else:
                                co_g_val = sel_co_guide if sel_co_guide != "NONE" else None
                                sme_val = sel_add_sme if sel_add_sme != "NONE" else None
                                ok, err = admin_respond_to_mentor(
                                    query_id=q_id,
                                    admin_id=admin_id,
                                    directive=directive_text.strip(),
                                    new_status=new_st,
                                    assign_co_guide_id=co_g_val,
                                    assign_sme_id=sme_val
                                )
                                if ok:
                                    st.session_state[f"admin_inquiry_directive_success_{q_id}"] = f"Directive recorded and dispatched to {mentor_name} ({mentor_role_lbl})!"
                                    st.rerun()
                                else:
                                    st.error(err or "Failed to issue directive.")

    # ─────────────────────────────────────────────────────────────
    # TAB 6: SCHEME CATALOGUE CRUD
    # ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────
    # TAB 6: SCHEME CATALOGUE CRUD
    # ─────────────────────────────────────────────────────────────
    with tabs[5]:
        st.subheader(f"Scheme Catalogue Management ({len(all_schemes)} Records in Intelligence Database)")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Full Administrative Authority: Search, filter, add new schemes, edit existing guidelines, toggle archive status, or permanently delete schemes from both local and cloud databases.</p>", unsafe_allow_html=True)

        # ── 1. ADD NEW SCHEME EXPANDER ──
        with st.expander("➕ Add New Scheme / Fund to Catalogue", expanded=False):
            with st.form("form_add_new_scheme"):
                st.markdown("##### Basic Information & Capital Structure")
                c_ns1, c_ns2 = st.columns(2)
                with c_ns1:
                    ns_name = st.text_input("Scheme / Fund Name *", placeholder="e.g. IndiaAI Mission Compute & Startup Support")
                    ns_agency = st.text_input("Agency / Ministry / Firm *", placeholder="e.g. MeitY (Ministry of Electronics and IT)")
                    ns_amount = st.text_input("Funding Amount *", placeholder="e.g. Up to 40% compute GPU subsidy + Rs 1 Crore grant")
                    ns_type_sel = st.selectbox("Funding / Capital Type", MASTER_FUNDING_TYPES)
                    ns_custom_type = ""
                    if ns_type_sel == "Other / Blended Capital (Specify)":
                        ns_custom_type = st.text_input("Specify Custom Capital Type *", placeholder="e.g. SAFE, Revenue Share", key="ns_custom_type")
                with c_ns2:
                    ns_cat_sel = st.selectbox("Category", MASTER_CATEGORY_TYPES)
                    ns_custom_cat = ""
                    if ns_cat_sel == "Other / Consortium (Specify)":
                        ns_custom_cat = st.text_input("Specify Custom Category *", placeholder="e.g. Global Consortium", key="ns_custom_cat")
                    ns_stage_sel = st.selectbox("Eligible Stage", MASTER_STAGES)
                    ns_custom_stage = ""
                    if ns_stage_sel == "Other / Multi-Stage (Specify)":
                        ns_custom_stage = st.text_input("Specify Custom Stage *", placeholder="e.g. Commercialization Phase", key="ns_custom_stage")
                    ns_scope_sel = st.selectbox("State Scope / Geography", MASTER_GEOGRAPHIC_SCOPES)
                    ns_custom_scope = ""
                    if ns_scope_sel == "Other / Specific Region (Specify)":
                        ns_custom_scope = st.text_input("Specify Custom Geography *", placeholder="e.g. South India / Tier 2 Cities", key="ns_custom_scope")
                    ns_url = st.text_input("Official Portal URL", placeholder="https://indiaai.gov.in")

                ns_sectors_sel = st.multiselect("Eligible Sectors *", MASTER_SECTORS, default=["Cross-Sector / All Sectors"])
                ns_custom_sec = ""
                if "Other / Not Listed (Specify)" in ns_sectors_sel:
                    ns_custom_sec = st.text_input("Specify Custom Sectors (comma-separated) *", placeholder="e.g. SpaceTech, Marine Culture", key="ns_custom_sec")

                c_ns3, c_ns4 = st.columns(2)
                with c_ns3:
                    ns_brief = st.text_input("One-line Brief", placeholder="Compute infrastructure subsidies and grant support for AI startups.")
                with c_ns4:
                    ns_desc = st.text_area("Full Description / Details", placeholder="Access to 10,000+ GPUs onboarded via empaneled providers plus cohort grants for AI ventures building sovereign IP.", height=68)

                st.markdown("##### Intelligence, Red Flags & Application Prompt")
                ns_agenda = st.text_area("🤫 Insider Intelligence / Hidden Agenda (One point per line)", placeholder=">> MeitY wants SOVEREIGN AI & Indigenous IP - show how your model reduces reliance on foreign foundations.\n>> Emphasize local Indian compute residency.")
                ns_flags = st.text_area("⚠️ Red Flags / Warnings (One point per line)", placeholder="!! Do not submit wrapper apps with no unique data or IP - auto-rejected.\n!! High technical bar during empaneled panel review.")
                ns_prompt = st.text_area("🤖 AI Pitch & Application Prompt (Template for founders)", placeholder="ROLE: Senior Startup Funding & VC Consultant\nTARGET FUND: [Fund Name]...", height=120)

                if st.form_submit_button("ADD SCHEME TO CATALOGUE", type="primary"):
                    if ns_name and ns_agency:
                        import uuid
                        final_type = ns_custom_type.strip() if (ns_type_sel == "Other / Blended Capital (Specify)" and ns_custom_type.strip()) else ns_type_sel
                        final_cat = ns_custom_cat.strip() if (ns_cat_sel == "Other / Consortium (Specify)" and ns_custom_cat.strip()) else ns_cat_sel
                        final_stage = ns_custom_stage.strip() if (ns_stage_sel == "Other / Multi-Stage (Specify)" and ns_custom_stage.strip()) else ns_stage_sel
                        final_scope = ns_custom_scope.strip() if (ns_scope_sel == "Other / Specific Region (Specify)" and ns_custom_scope.strip()) else ns_scope_sel

                        final_sectors = [s for s in ns_sectors_sel if s != "Other / Not Listed (Specify)"]
                        if ns_custom_sec and ns_custom_sec.strip():
                            final_sectors.extend([x.strip() for x in ns_custom_sec.split(",") if x.strip()])
                        if not final_sectors:
                            final_sectors = ["Cross-Sector / All Sectors"]

                        new_agenda = [x.strip() for x in ns_agenda.split("\n") if x.strip()] if ns_agenda else [">> High impact venture creation."]
                        new_flags = [x.strip() for x in ns_flags.split("\n") if x.strip()] if ns_flags else ["!! Review official guidelines before applying."]
                        new_s_obj = {
                            "id": f"SCH-ADMIN-{uuid.uuid4().hex[:8].upper()}",
                            "name": ns_name,
                            "agency": ns_agency,
                            "category_type": final_cat,
                            "funding_type": final_type,
                            "scheme_type": final_type,
                            "stage": final_stage,
                            "amount": ns_amount,
                            "brief": ns_brief or ns_name,
                            "description": ns_desc or ns_brief or ns_name,
                            "sectors": final_sectors,
                            "hidden_agenda": new_agenda,
                            "red_flags": new_flags,
                            "application_prompt": ns_prompt or f"ROLE: Senior Startup Funding & VC Consultant\nTARGET FUND: {ns_name} ({ns_agency})\nFUND TYPE: {final_type}",
                            "state_scope": final_scope,
                            "geography": "National" if final_scope == "All India" else "State",
                            "application_url": ns_url,
                            "last_verified": "September 2026",
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
            sc_cat = st.selectbox("Category", ["ALL"] + MASTER_CATEGORY_TYPES, key="adm_sc_cat")
        with c_f3:
            sc_stage = st.selectbox("Stage", ["ALL"] + MASTER_STAGES, key="adm_sc_stage")
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
            page_size_option = st.selectbox("Schemes per page", [15, 30, 50, 100, f"Show All ({total_count})"], index=1, key="adm_page_size")

        if str(page_size_option).startswith("Show All"):
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
            if st.button("◀ Previous Page", disabled=(st.session_state.adm_scheme_page <= 1), use_container_width=True, key="adm_sc_btn_prev"):
                st.session_state.adm_scheme_page -= 1
                st.rerun()
        with c_p2:
            st.markdown(f"<div style='text-align:center; padding-top:6px; font-weight:600; color:#475569;'>Page {st.session_state.adm_scheme_page} of {total_pages} ({total_count} Total Schemes)</div>", unsafe_allow_html=True)
        with c_p3:
            if st.button("Next Page ▶", disabled=(st.session_state.adm_scheme_page >= total_pages), use_container_width=True, key="adm_sc_btn_next"):
                st.session_state.adm_scheme_page += 1
                st.rerun()

        start_idx = (st.session_state.adm_scheme_page - 1) * page_size
        end_idx = start_idx + page_size
        page_schemes = all_matches[start_idx:end_idx]

        if not page_schemes:
            st.info("No schemes match your search criteria. Try clearing search keywords or resetting filters.")
        else:
            # ── 4. RICH PLAYBOOK FUND EXPLORER CARDS WITH FULL EDIT & DELETE (3-COLUMN GRID) ──
            cols_per_row = 3
            for i in range(0, len(page_schemes), cols_per_row):
                row_schemes = page_schemes[i : i + cols_per_row]
                cols = st.columns(3)
                for j, s in enumerate(row_schemes):
                    with cols[j]:
                        render_fund_explorer_card(s, is_admin=True, admin_id=admin_id, key_prefix=f"adm_sc_{s['id']}")
