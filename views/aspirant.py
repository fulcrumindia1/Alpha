"""
pages/aspirant.py — Aspirant Dashboard for FULCRUM-INDIA (Cluster A)
===================================================================
Aspirant Experience:
- Dashboard: Overview, Profile completion, My Guide, My SME, Schemes preview.
- Profile: 4-part Naukri/LinkedIn profile (Personal, Professional, Business, Demographics).
- My Guide / My SME: View assigned mentor credentials.
- My Journey: Chronological timeline with [ + Add Journey Entry ] and edit/delete permissions.
- Scheme Matches: Deterministic recommendations with "Why this matched".
- Help: Raise support ticket and track status.
"""

import streamlit as st
import html
from datetime import datetime, date
from services.profiles import get_profile, update_aspirant_profile
from services.relationships import get_aspirant_mentors
from services.journey import get_journey_timeline, add_manual_aspirant_entry, soft_delete_event, get_standard_role_label, toggle_event_roadmap_inclusion
from services.schemes import get_released_schemes_for_aspirant
from services.schemes_ui import render_fund_explorer_card
from services.help_requests import create_request, list_requests
from services.constants import (
    MASTER_SECTORS,
    MASTER_STAGES,
    STAGE_DESCRIPTIONS,
    MASTER_DISTRICTS_TN,
    MASTER_BUSINESS_TYPES,
    MASTER_SOCIAL_CATEGORIES,
    MASTER_GENDERS,
    resolve_field_choice
)

def render_aspirant_portal(user_profile: dict):
    user_id = user_profile["id"]
    profile = get_profile(user_id) or user_profile

    full_name = profile.get("full_name", "Entrepreneur")
    completion_pct = profile.get("completion_pct", 50)
    mentors = get_aspirant_mentors(user_id)
    guide = mentors.get("guide")
    sme = mentors.get("sme")

    # Top Header
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #E2E8F0;">
        <div>
            <div style="font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #2563EB;">Aspirant Dashboard</div>
            <h1 style="font-size: 2rem; font-weight: 800; margin: 0; color: #0F172A;">Welcome, {full_name} 👋</h1>
            <p style="font-size: 0.95rem; color: #475569; margin-top: 0.25rem;">
                {profile.get("profile_data", {}).get("business", {}).get("business_name") or "Your Enterprise"} · {profile.get("district", "Tamil Nadu")}
            </p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 4px;">Profile Completion: <strong style="color:#0F172A;">{completion_pct}%</strong></div>
            <div style="width: 140px; height: 8px; background: #E2E8F0; border-radius: 100px; overflow: hidden;">
                <div style="width: {completion_pct}%; height: 100%; background: linear-gradient(90deg, #2563EB, #10b981); border-radius: 100px;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Tabs
    tabs = st.tabs([
        "📊 Overview",
        "👤 My Profile",
        "🎬 My Journey",
        "🤝 My Mentors",
        "🏦 Scheme Matches",
        "🤝 Consult a Guide or SME"
    ])

    # ─────────────────────────────────────────────────────────────
    # TAB 1: OVERVIEW
    # ─────────────────────────────────────────────────────────────
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-bottom: 3px solid #6366f1; border-radius: 14px; padding: 1.2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Profile Status</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #0F172A; margin-top: 0.2rem;">{completion_pct}%</div>
                <div style="font-size: 0.75rem; color: #059669; font-weight: 600;">{'Ready for Matching' if completion_pct >= 60 else 'Complete more fields'}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            g_text = guide.get("full_name") if guide else "Pending Admin Assignment"
            st.markdown(f"""
            <div class="metric-card" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-bottom: 3px solid #10b981; border-radius: 14px; padding: 1.2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">My Dedicated Guide</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-top: 0.4rem;">{g_text}</div>
                <div style="font-size: 0.75rem; color: #64748B;">{guide.get('profile_data',{}).get('expertise','Assigned by Admin') if guide else 'Contact Admin for Guide'}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            s_text = sme.get("full_name") if sme else "Not Assigned"
            st.markdown(f"""
            <div class="metric-card" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-bottom: 3px solid #f59e0b; border-radius: 14px; padding: 1.2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Domain SME</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-top: 0.4rem;">{s_text}</div>
                <div style="font-size: 0.75rem; color: #64748B;">{sme.get('profile_data',{}).get('expertise','Specialist') if sme else 'For GST, FSSAI, Patents'}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            released_schemes = get_released_schemes_for_aspirant(user_id)
            st.markdown(f"""
            <div class="metric-card" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-bottom: 3px solid #ec4899; border-radius: 14px; padding: 1.2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Released Schemes</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #0F172A; margin-top: 0.2rem;">{len(released_schemes)}</div>
                <div style="font-size: 0.75rem; color: #2563EB; font-weight: 600;">Curated by Guide</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        # Recent Journey Activity Preview
        st.subheader("🎬 Journey Highlights")
        timeline = get_journey_timeline(user_id)
        active_events = [e for e in (timeline or []) if e.get("included_in_roadmap", True) is not False]
        if active_events:
            recent_events = active_events[:3]
            for e in recent_events:
                actor_role = e.get("actor_role", "aspirant")
                actor_name = e.get("actor_name")
                if not actor_name:
                    if actor_role == "aspirant":
                        actor_name = full_name or "Entrepreneur"
                    elif actor_role == "system":
                        actor_name = "Platform Intelligence"
                    elif actor_role == "guide":
                        actor_name = "Dedicated Guide"
                    elif actor_role == "sme":
                        actor_name = "Domain SME"
                    else:
                        actor_name = "Advisory Council"
                elif actor_role == "system":
                    actor_name = "Platform Intelligence"
                std_role = get_standard_role_label(actor_role, is_aspirant_facing=True)
                role_color = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#64748b"
                date_str = str(e.get("event_date", ""))[:10]
                ev_data = e.get("event_data", {})
                st.markdown(f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {role_color}; border-radius: 0 10px 10px 0; padding: 1rem 1.2rem; margin-bottom: 0.75rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#0F172A; font-size:1rem;">{ev_data.get('title') or e.get('event_type')}</strong>
                        <span style="font-size:0.75rem; color:#64748B; font-weight:600;">{date_str}</span>
                    </div>
                    <div style="color:#334155; font-size:0.88rem; margin-top:0.3rem;">{ev_data.get('description','')}</div>
                    <div style="margin-top:0.4rem; font-size:0.75rem; color:{role_color}; font-weight:700;">
                        Contributor: <strong>{actor_name}</strong> ({std_role})
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No journey records yet. Add your first entry in the 'My Journey' tab!")

    # ─────────────────────────────────────────────────────────────
    # TAB 2: MY PROFILE (Naukri/LinkedIn Style)
    # ─────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 📋 Entrepreneur Profile")
        st.markdown("<p style='color:#475569; font-size:0.9rem;'>Keep this profile updated. Changes automatically recalculate your recommended funding schemes and record journey updates.</p>", unsafe_allow_html=True)

        p_data = profile.get("profile_data", {})
        cur_personal = p_data.get("personal", {})
        cur_prof = p_data.get("professional", {})
        cur_biz = p_data.get("business", {})
        cur_demo = p_data.get("demographics", {})

        with st.form("form_update_profile"):
            # SECTION 1: PERSONAL
            st.markdown("#### 1. Personal Information")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                f_name = st.text_input("Full Name *", value=profile.get("full_name", ""))
                f_email = st.text_input("Email (Login)", value=profile.get("email", ""), disabled=True)
            with col_p2:
                f_phone = st.text_input("Phone *", value=profile.get("phone", ""))
                cur_gen = cur_personal.get("gender", "Male")
                gen_idx, gen_custom = resolve_field_choice(cur_gen, MASTER_GENDERS, "Other / Prefer Not to Say")
                f_gender_sel = st.selectbox("Gender", MASTER_GENDERS, index=gen_idx)
                f_gender = f_gender_sel
                if f_gender_sel == "Other / Prefer Not to Say":
                    f_gen_c = st.text_input("Specify Gender (Optional)", value=gen_custom, key="prof_custom_gender")
                    if f_gen_c and f_gen_c.strip():
                        f_gender = f_gen_c.strip()
            with col_p3:
                f_dob = st.text_input("Date of Birth (DD-MM-YYYY)", value=cur_personal.get("dob", "15-08-1995"))
                f_address = st.text_input("Address", value=cur_personal.get("address", ""))

            # SECTION 2: PROFESSIONAL
            st.markdown("#### 2. Professional Background")
            col_pr1, col_pr2 = st.columns(2)
            with col_pr1:
                f_edu = st.text_input("Education / Qualification", value=cur_prof.get("education", "B.Tech / Graduate"))
                f_skills = st.text_input("Key Skills (comma separated)", value=cur_prof.get("skills", "Product Development, Organic Processing, Operations"))
            with col_pr2:
                f_exp = st.text_input("Previous Experience", value=cur_prof.get("experience", "3 years in food manufacturing"))
                f_certs = st.text_input("Certifications / Training", value=cur_prof.get("certifications", "FSSAI Basic, MSME EDI Training"))

            # SECTION 3: BUSINESS
            st.markdown("#### 3. Business & Venture Details")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                b_name = st.text_input("Business Name *", value=cur_biz.get("business_name", "Madurai Millet Naturals"))
                cur_btype = cur_biz.get("business_type", "Manufacturing")
                btype_idx, btype_custom = resolve_field_choice(cur_btype, MASTER_BUSINESS_TYPES, "Other / Hybrid (Specify)")
                b_type_sel = st.selectbox("Business Type *", MASTER_BUSINESS_TYPES, index=btype_idx)
                b_type = b_type_sel
                if b_type_sel == "Other / Hybrid (Specify)":
                    b_type_custom_in = st.text_input("Specify Business Type *", value=btype_custom, placeholder="e.g. Contract R&D / Hybrid Studio", key="prof_custom_btype")
                    if b_type_custom_in and b_type_custom_in.strip():
                        b_type = b_type_custom_in.strip()
            with col_b2:
                cur_sec = cur_biz.get("sector", "Food Processing & Agribusiness")
                sec_idx, sec_custom = resolve_field_choice(cur_sec, MASTER_SECTORS, "Other / Not Listed (Specify)")
                b_sector_sel = st.selectbox("Industry Sector *", MASTER_SECTORS, index=sec_idx)
                b_sector = b_sector_sel
                if b_sector_sel == "Other / Not Listed (Specify)":
                    b_sec_custom_in = st.text_input("Specify Custom Industry Sector *", value=sec_custom, placeholder="e.g. SpaceTech, Marine Biotechnology", key="prof_custom_sec")
                    if b_sec_custom_in and b_sec_custom_in.strip():
                        b_sector = b_sec_custom_in.strip()

                cur_stg = cur_biz.get("stage", "Pre-Seed / Seed")
                stg_idx, stg_custom = resolve_field_choice(cur_stg, MASTER_STAGES, "Other / Multi-Stage (Specify)", default_index=1)
                b_stage_sel = st.selectbox("Development Stage *", MASTER_STAGES, index=stg_idx)
                st.caption(f"ℹ️ {STAGE_DESCRIPTIONS.get(b_stage_sel, '')}")
                b_stage = b_stage_sel
                if b_stage_sel == "Other / Multi-Stage (Specify)":
                    b_stg_custom_in = st.text_input("Specify Development Stage *", value=stg_custom, placeholder="e.g. Commercialization Phase", key="prof_custom_stg")
                    if b_stg_custom_in and b_stg_custom_in.strip():
                        b_stage = b_stg_custom_in.strip()
            with col_b3:
                b_revenue = st.text_input("Annual Revenue / MRR", value=cur_biz.get("revenue", "₹12,00,000 / year"))
                b_team = st.number_input("Employee Count", min_value=0, max_value=500, value=int(cur_biz.get("employee_count", 3)))

            b_desc = st.text_area("Business Description", value=cur_biz.get("description", "Manufacturing and direct packaging of traditional millet products, porridge mixes, and healthy snacks."))

            # SECTION 4: DEMOGRAPHICS & SPECIAL ELIGIBILITY
            st.markdown("#### 4. Demographics & Scheme Eligibility")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                cur_dist = profile.get("district") or cur_demo.get("district") or "Madurai"
                dist_idx, dist_custom = resolve_field_choice(cur_dist, MASTER_DISTRICTS_TN, "Other District / Non-TN (Specify)", default_index=13)
                d_dist_sel = st.selectbox("District *", MASTER_DISTRICTS_TN, index=dist_idx)
                d_final_district = d_dist_sel
                if d_dist_sel == "Other District / Non-TN (Specify)":
                    d_other_dist = st.text_input("Specify District / City / State *", value=dist_custom, placeholder="e.g. Bengaluru (Karnataka), Mumbai (Maharashtra)", key="profile_other_district")
                    if d_other_dist and d_other_dist.strip():
                        d_final_district = d_other_dist.strip()
                is_tn = d_dist_sel != "Other District / Non-TN (Specify)"
                d_state = st.text_input("State", value="Tamil Nadu" if is_tn else "Other State", disabled=True)
            with col_d2:
                cur_cat = cur_demo.get("founder_category", "OBC")
                cat_idx, cat_custom = resolve_field_choice(cur_cat, MASTER_SOCIAL_CATEGORIES, "Other / Prefer Not to Disclose", default_index=1)
                d_cat_sel = st.selectbox("Founder Category (for Subsidies)", MASTER_SOCIAL_CATEGORIES, index=cat_idx)
                st.caption("ℹ️ Used for statutory affirmative quotas (e.g. Special capital subsidies for SC/ST/OBC).")
                d_cat = d_cat_sel
                if d_cat_sel == "Other / Prefer Not to Disclose":
                    d_cat_custom_in = st.text_input("Specify Category (Optional)", value=cat_custom, placeholder="e.g. Special Category", key="prof_custom_cat")
                    if d_cat_custom_in and d_cat_custom_in.strip():
                        d_cat = d_cat_custom_in.strip()
            with col_d3:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; margin-bottom:0.3rem;'>Special Registrations & Quotas</p>", unsafe_allow_html=True)
                d_dpiit = st.checkbox("DPIIT Recognized Startup", value=bool(cur_demo.get("is_dpiit_recognized", True)))
                d_startuptn = st.checkbox("StartupTN Registered", value=bool(cur_demo.get("is_startuptn_registered", True)))
                is_female_founder = (f_gender == "Female")
                d_women = st.checkbox("Women-Led Enterprise (Primary Founder is Female)", value=bool(cur_demo.get("is_women_led", is_female_founder)))
                default_equity = int(cur_demo.get("women_equity_pct", 100 if d_women else 0))
                d_women_equity = st.number_input("Women Co-Founder Equity %", min_value=0, max_value=100, value=default_equity, help="Total women shareholding % (Schemes like TWEES mandate ≥51% women ownership).")
                is_qualifies_women = bool(d_women or d_women_equity >= 51)

            btn_save = st.form_submit_button("SAVE PROFILE & UPDATE MATCHES", type="primary", use_container_width=True)

            if btn_save:
                updated, err = update_aspirant_profile(
                    user_id=user_id,
                    full_name=f_name,
                    phone=f_phone,
                    district=d_final_district,
                    state=d_state,
                    personal_data={"gender": f_gender, "dob": f_dob, "address": f_address},
                    professional_data={"education": f_edu, "skills": f_skills, "experience": f_exp, "certifications": f_certs},
                    business_data={"business_name": b_name, "business_type": b_type, "sector": b_sector, "stage": b_stage, "revenue": b_revenue, "employee_count": b_team, "description": b_desc},
                    demographics_data={"district": d_final_district, "state": d_state, "founder_category": d_cat, "gender": f_gender, "is_dpiit_recognized": d_dpiit, "is_startuptn_registered": d_startuptn, "is_women_led": is_qualifies_women, "women_equity_pct": d_women_equity}
                )
                if updated:
                    st.success("✅ Profile updated! Scheme recommendations recalculated and Journey event logged.")
                    st.rerun()
                else:
                    st.error(err or "Failed to update profile.")

    # ─────────────────────────────────────────────────────────────
    # TAB 3: MY JOURNEY (The Core Movie / Timeline)
    # ─────────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 🎬 The Entrepreneur's Journey")
        st.markdown("<p style='color:#475569; font-size:0.9rem;'>The living story of your venture. Every milestone, mentor session, and operational breakthrough is preserved here.</p>", unsafe_allow_html=True)

        with st.expander("➕ Add Journey Milestone / Entry", expanded=False):
            with st.form("form_add_journey_entry"):
                j_title = st.text_input("Title", placeholder="e.g. Started Business, Launched Product, Made First Sale")
                col_je1, col_je2 = st.columns(2)
                with col_je1:
                    j_date = st.date_input("Event Date", value=date.today())
                with col_je2:
                    j_cat = st.selectbox("Category", ["Inception", "Product", "Sales", "Team", "Operations", "Milestone"])
                j_desc = st.text_area("What happened?", placeholder="Started selling millet porridge packs from our home kitchen to test customer appetite.")

                if st.form_submit_button("ADD TO MY JOURNEY", type="primary"):
                    if j_title and j_desc:
                        ev, err = add_manual_aspirant_entry(
                            aspirant_id=user_id,
                            title=j_title,
                            description=j_desc,
                            category=j_cat,
                            event_date=j_date.isoformat()
                        )
                        if ev:
                            st.success(f"Added '{j_title}' to your Journey!")
                            st.rerun()
                        else:
                            st.error(err or "Could not save entry.")
                    else:
                        st.warning("Please provide both title and description.")

        # Display Chronological Timeline
        timeline = get_journey_timeline(user_id)
        if not timeline:
            st.info("Your journey is waiting for its first scene. Use the form above to add an entry!")
        else:
            st.markdown("---")
            for idx, event in enumerate(timeline):
                actor_role = event.get("actor_role", "aspirant")
                actor_name = event.get("actor_name")
                if not actor_name:
                    if actor_role == "aspirant":
                        actor_name = full_name or "Entrepreneur"
                    elif actor_role == "system":
                        actor_name = "Platform Intelligence"
                    elif actor_role == "guide":
                        actor_name = "Dedicated Guide"
                    elif actor_role == "sme":
                        actor_name = "Domain SME"
                    else:
                        actor_name = "Advisory Council"
                elif actor_role == "system":
                    actor_name = "Platform Intelligence"
                std_role = get_standard_role_label(actor_role, is_aspirant_facing=True)
                ev_data = event.get("event_data", {})
                raw_title = ev_data.get("title") or event.get("event_type") or "Milestone"
                raw_desc = ev_data.get("description", "")
                title = html.escape(str(raw_title))
                desc = html.escape(str(raw_desc)).replace("\n", "<br>")
                date_display = str(event.get("event_date", ""))[:10]

                # Role-specific styling
                badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#64748b"

                is_included = event.get("included_in_roadmap", True) is not False
                if is_included:
                    status_badge = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; padding:2px 8px; border-radius:6px;">✓ Active on Roadmap</span>'
                    card_border = "border:1px solid #E2E8F0;"
                    card_bg = "background:#FFFFFF;"
                else:
                    status_badge = '<span style="display:inline-block; font-size:0.72rem; font-weight:700; background:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:2px 8px; border-radius:6px;">✕ Excluded (Marked Not Needed)</span>'
                    card_border = "border:1px dashed #CBD5E1;"
                    card_bg = "background:#F8FAFC;"

                col_time, col_body, col_del = st.columns([1.2, 4.8, 1.2])
                with col_time:
                    st.markdown(f"""
                    <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                    <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{std_role}</span>
                    """, unsafe_allow_html=True)
                with col_body:
                    st.markdown(f"""
                    <div style="{card_bg} {card_border} border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">{title}</div>
                            <div>{status_badge}</div>
                        </div>
                        <div style="color:#334155; font-size:0.9rem; margin-top:0.3rem; line-height:1.5;">{desc}</div>
                        <div style="font-size:0.75rem; color:#64748B; margin-top:0.4rem;">Contributor: <strong>{actor_name}</strong> ({std_role})</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    # Aspirants can delete only their own manual entries
                    if actor_role == "aspirant":
                        if st.button("🗑️", key=f"del_ev_{event['id']}", help="Delete your entry"):
                            soft_delete_event(event["id"], user_id, "aspirant")
                            st.rerun()
                    else:
                        # For mentor/guide/sme contributions, founder can toggle Needed or Not Needed
                        if is_included:
                            if st.button("✕ Not Needed", key=f"btn_toggle_{event['id']}", help="Mark this contribution as not needed for your roadmap"):
                                toggle_event_roadmap_inclusion(event["id"], user_id, False)
                                st.rerun()
                        else:
                            if st.button("✓ Needed", key=f"btn_toggle_{event['id']}", help="Include this contribution on your roadmap"):
                                toggle_event_roadmap_inclusion(event["id"], user_id, True)
                                st.rerun()

    # ─────────────────────────────────────────────────────────────
    # TAB 4: MY MENTORS
    # ─────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 🤝 Dedicated Guidance Team")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("#### 🧭 Your Assigned Guide")
            if guide:
                g_p = guide.get("profile_data", {})
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #10b981; border-radius:14px; padding:1.5rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="font-size:1.3rem; font-weight:800; color:#0F172A;">{guide.get('full_name')}</div>
                    <div style="color:#059669; font-size:0.85rem; font-weight:600; margin-bottom:0.75rem;">Dedicated Enterprise Mentor</div>
                    <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Expertise:</strong> {g_p.get('expertise', 'Business Guidance & Planning')}</p>
                    <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Location:</strong> {guide.get('district', 'Tamil Nadu')}</p>
                    <p style="font-size:0.85rem; color:#64748B; margin-top:0.75rem;"><em>"{g_p.get('bio', 'Assigned by Fulcrum-India Admin to assist in strategy and loan execution.')}"</em></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No Guide assigned yet. The Administrator reviews new profiles and assigns a local Guide.")

        with col_m2:
            smes = mentors.get("smes", [])
            if not smes and sme:
                smes = [sme]
            smes_count = len(smes)
            header_title = f"🔬 Domain Advisory Panel ({smes_count} Specialists)" if smes_count > 1 else "🔬 Your Assigned Domain SME"
            st.markdown(f"#### {header_title}")
            if smes:
                for idx, s_item in enumerate(smes):
                    s_p = s_item.get("profile_data", {})
                    s_name = s_item.get("full_name", "Specialist")
                    s_exp = s_p.get("expertise") or s_p.get("industry") or "Technical & Compliance Advisory"
                    s_ind = s_p.get("industry") or "Specialized Domain"
                    s_bio = s_p.get("bio") or "Assigned to provide specialized technical audit and compliance guidance."
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:14px; padding:1.25rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-size:1.2rem; font-weight:800; color:#0F172A;">{s_name}</div>
                        </div>
                        <div style="color:#D97706; font-size:0.85rem; font-weight:600; margin-bottom:0.75rem;">Subject Matter Expert · Specialist #{idx+1}</div>
                        <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Specialization:</strong> {s_exp}</p>
                        <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Industry:</strong> {s_ind}</p>
                        <p style="font-size:0.85rem; color:#64748B; margin-top:0.75rem;"><em>"{s_bio}"</em></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No SME assigned yet. If you need specialized help in GST, FSSAI, or Patents, submit a request under 'Help'.")

    # ─────────────────────────────────────────────────────────────
    # TAB 5: SCHEME MATCHES (Gatekeeper Governed)
    # ─────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🏦 Recommended Funding Schemes")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Curated government schemes and venture capital opportunities reviewed and released to your venture by your dedicated Guide.</p>", unsafe_allow_html=True)

        released_schemes = get_released_schemes_for_aspirant(user_id)

        if not released_schemes:
            st.markdown("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:2.5rem 1.5rem; text-align:center;">
                <h3 style="color:#0F172A; margin:0 0 0.5rem 0;">No schemes have been released to you yet.</h3>
                <p style="color:#64748B; font-size:0.95rem; max-width:540px; margin:0 auto; line-height:1.5;">
                    Your Guide reviews relevant funding opportunities and will release appropriate schemes to your account when ready.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"Your Guide has released **{len(released_schemes)}** curated funding opportunities for your venture!")
            cols_per_row = 3
            for i in range(0, len(released_schemes), cols_per_row):
                row_schemes = released_schemes[i : i + cols_per_row]
                cols = st.columns(3)
                for j, s in enumerate(row_schemes):
                    with cols[j]:
                        render_fund_explorer_card(
                            s,
                            is_admin=False,
                            key_prefix=f"asp_rel_{s.get('id', j)}",
                            show_private_intelligence=False,
                            guide_recommendation=s.get("guide_recommendation")
                        )

    # ─────────────────────────────────────────────────────────────
    # TAB 6: CONSULT A GUIDE OR SME (Strictly Guides and SMEs)
    # ─────────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 🤝 Consult a Guide or SME")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Need guidance on scheme applications, DPR preparation, GST compliance, or technical mentoring? Submit a consultation request directly to your assigned Guide or Domain SME.</p>", unsafe_allow_html=True)

        mentors = get_aspirant_mentors(user_id)
        g_assigned = mentors.get("guide")
        s_assigned = mentors.get("sme")
        smes_assigned = mentors.get("smes") or ([s_assigned] if s_assigned else [])

        guide_disp_name = g_assigned.get("full_name") if g_assigned else "Guide Pending Assignment"
        sme_names_list = [s.get("full_name") for s in smes_assigned if s.get("full_name")]
        sme_disp_name = ", ".join(sme_names_list) if sme_names_list else "Domain Specialist Pending Assignment"

        with st.form("form_help"):
            col_hp_sub, col_hp_cat = st.columns([3, 2])
            with col_hp_sub:
                h_subj = st.text_input("Subject", placeholder="e.g. GST Registration, Bank Proposal Review, PMEGP Quotations")
            with col_hp_cat:
                category_options = {
                    "GENERAL": f"🧭 General Mentorship → Dedicated Guide ({guide_disp_name})",
                    "BANKING_DPR": f"🏦 Banking & DPR Review → Dedicated Guide ({guide_disp_name})",
                    "GST_TAXATION": f"🧾 GST & Taxation → Domain SME ({sme_disp_name})",
                    "LEGAL_COMPLIANCE": f"📜 Legal & Corporate → Domain SME ({sme_disp_name})",
                    "FSSAI_FOOD": f"🧪 FSSAI & Quality → Domain SME ({sme_disp_name})",
                    "PATENTS_IPR": f"💡 Patents & IP → Domain SME ({sme_disp_name})"
                }
                h_cat_key = st.selectbox(
                    "Help Topic / Category",
                    options=list(category_options.keys()),
                    format_func=lambda k: category_options[k],
                    index=0
                )

            col_hp1, col_hp2 = st.columns([3, 1])
            with col_hp1:
                h_msg = st.text_area("Message / Description", placeholder="Describe exactly what you need help with...")
            with col_hp2:
                h_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)

            # Determine routing preview
            target_role = "sme" if h_cat_key in ("GST_TAXATION", "LEGAL_COMPLIANCE", "FSSAI_FOOD", "PATENTS_IPR") else "guide"
            target_person = sme_disp_name if target_role == "sme" else guide_disp_name
            target_label = "Domain SME (Subject Matter Expert)" if target_role == "sme" else "Dedicated Guide"

            st.markdown(f"""
            <div style="background:{'#FFFBEB' if target_role == 'sme' else '#F0FDF4'}; border:1px solid {'#FDE68A' if target_role == 'sme' else '#BBF7D0'}; border-left:4px solid {'#F59E0B' if target_role == 'sme' else '#10B981'}; border-radius:0 8px 8px 0; padding:0.75rem 1rem; margin-top:0.6rem; margin-bottom:0.75rem;">
                <div style="font-weight:800; color:{'#92400E' if target_role == 'sme' else '#166534'}; font-size:0.88rem;">🎯 Direct Delivery: Routed to {target_label} — <strong>{target_person}</strong></div>
                <div style="color:{'#92400E' if target_role == 'sme' else '#166534'}; font-size:0.8rem; margin-top:2px;">Sent directly to your assigned mentor. Institutional administrators do not receive or intermediate routine guidance tickets.</div>
            </div>
            """, unsafe_allow_html=True)

            if st.form_submit_button("SUBMIT CONSULTATION REQUEST", type="primary"):
                req, err = create_request(user_id, h_subj, h_msg, h_prio, category=h_cat_key, target_role=target_role)
                if req:
                    st.success(f"Consultation request submitted! Routed directly to your {target_label} ({target_person}).")
                    st.rerun()
                else:
                    st.error(err or "Failed to submit request.")

        st.markdown("#### 📋 Consultation History")
        my_reqs = list_requests(aspirant_id=user_id)
        if not my_reqs:
            st.info("No consultation requests submitted yet.")
        else:
            for r in my_reqs:
                st_color = "#f59e0b" if r["status"] == "OPEN" else "#3b82f6" if r["status"] == "IN_PROGRESS" else "#10b981"
                cat_badge = r.get("category", "GENERAL").replace("_", " ")
                g_resp_html = f'<div style="background:#EFF6FF; border-left:3px solid #3B82F6; border:1px solid #BFDBFE; padding:0.5rem 0.75rem; border-radius:0 6px 6px 0; font-size:0.85rem; color:#1E40AF; margin-top:0.5rem;"><strong>🧭 Guide Response:</strong> {r["guide_response"]}</div>' if r.get('guide_response') else ''
                s_resp_html = f'<div style="background:#FFFBEB; border-left:3px solid #F59E0B; border:1px solid #FDE68A; padding:0.5rem 0.75rem; border-radius:0 6px 6px 0; font-size:0.85rem; color:#92400E; margin-top:0.5rem;"><strong>🔬 SME Advisory Response:</strong> {r["sme_response"]}</div>' if r.get('sme_response') else ''

                card_html = (
                    f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem; margin-bottom:0.85rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<div><strong style="color:#0F172A; font-size:1.05rem;">{r["subject"]}</strong>'
                    f'<span style="background:#F1F5F9; color:#475569; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; margin-left:8px;">{cat_badge}</span></div>'
                    f'<span style="background:{st_color}; color:#ffffff; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:6px;">{r["status"]}</span>'
                    f'</div>'
                    f'<div style="color:#334155; font-size:0.9rem; margin:0.5rem 0;">{r["message"]}</div>'
                    f'{g_resp_html}'
                    f'{s_resp_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
