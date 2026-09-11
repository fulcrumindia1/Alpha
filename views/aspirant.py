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
from datetime import datetime, date
from services.profiles import get_profile, update_aspirant_profile
from services.relationships import get_aspirant_mentors
from services.journey import get_journey_timeline, add_manual_aspirant_entry, soft_delete_event
from services.schemes import match_schemes_for_aspirant, list_schemes
from services.help_requests import create_request, list_requests

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
        "💬 Help / Support"
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
            matched_schemes = match_schemes_for_aspirant(user_id)
            st.markdown(f"""
            <div class="metric-card" style="background: #FFFFFF; border: 1px solid #E2E8F0; border-bottom: 3px solid #ec4899; border-radius: 14px; padding: 1.2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Matched Schemes</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #0F172A; margin-top: 0.2rem;">{len(matched_schemes)}</div>
                <div style="font-size: 0.75rem; color: #2563EB; font-weight: 600;">Govt & Private Options</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        # Recent Journey Activity Preview
        st.subheader("🎬 Journey Highlights")
        timeline = get_journey_timeline(user_id)
        if timeline:
            recent_events = timeline[-3:]
            for e in reversed(recent_events):
                role_color = "#6366f1" if e.get("actor_role") == "aspirant" else "#10b981" if e.get("actor_role") == "guide" else "#f59e0b" if e.get("actor_role") == "sme" else "#64748b"
                date_str = str(e.get("event_date", ""))[:10]
                ev_data = e.get("event_data", {})
                st.markdown(f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {role_color}; border-radius: 0 10px 10px 0; padding: 1rem 1.2rem; margin-bottom: 0.75rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#0F172A; font-size:1rem;">{ev_data.get('title') or e.get('event_type')}</strong>
                        <span style="font-size:0.75rem; color:#64748B; font-weight:600;">{date_str}</span>
                    </div>
                    <div style="color:#334155; font-size:0.88rem; margin-top:0.3rem;">{ev_data.get('description','')}</div>
                    <div style="margin-top:0.4rem; font-size:0.75rem; color:{role_color}; font-weight:700; text-transform:uppercase;">
                        Actor: {e.get('actor_role')} ({e.get('actor_name') or 'Self'})
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
        st.markdown("<p style='color:#94a3b8; font-size:0.9rem;'>Keep this profile updated. Changes automatically recalculate your recommended funding schemes and record journey updates.</p>", unsafe_allow_html=True)

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
                f_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=0 if cur_personal.get("gender") != "Female" else 1)
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
                b_type = st.selectbox("Business Type", ["Manufacturing", "Services", "Trading", "Tech / SaaS", "Agri & Processing"], index=0)
            with col_b2:
                b_sector = st.selectbox("Industry Sector *", [
                    "Agri", "Food Processing", "Technology", "Manufacturing", "SaaS", "DeepTech", "Healthcare", "Fintech", "Consumer", "GreenTech"
                ], index=1)
                b_stage = st.selectbox("Development Stage *", [
                    "Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"
                ], index=1)
            with col_b3:
                b_revenue = st.text_input("Annual Revenue / MRR", value=cur_biz.get("revenue", "₹12,00,000 / year"))
                b_team = st.number_input("Employee Count", min_value=0, max_value=500, value=int(cur_biz.get("employee_count", 3)))

            b_desc = st.text_area("Business Description", value=cur_biz.get("description", "Manufacturing and direct packaging of traditional millet products, porridge mixes, and healthy snacks."))

            # SECTION 4: DEMOGRAPHICS & SPECIAL ELIGIBILITY
            st.markdown("#### 4. Demographics & Scheme Eligibility")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                d_dist = st.selectbox("District *", [
                    "Madurai", "Chennai", "Coimbatore", "Salem", "Trichy", "Tirunelveli", "Erode", "Vellore", "Thanjavur", "Dindigul", "Other"
                ], index=0)
                d_state = st.text_input("State", value="Tamil Nadu", disabled=True)
            with col_d2:
                d_cat = st.selectbox("Founder Category (for Subsidies)", ["General", "OBC", "SC", "ST", "Minority"], index=1)
            with col_d3:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; margin-bottom:0.5rem;'>Special Registrations</p>", unsafe_allow_html=True)
                d_dpiit = st.checkbox("DPIIT Recognized Startup", value=bool(cur_demo.get("is_dpiit_recognized", True)))
                d_startuptn = st.checkbox("StartupTN Registered", value=bool(cur_demo.get("is_startuptn_registered", True)))
                d_women = st.checkbox("Women-Led Enterprise", value=bool(cur_demo.get("is_women_led", False)))

            btn_save = st.form_submit_button("SAVE PROFILE & UPDATE MATCHES", type="primary", use_container_width=True)

            if btn_save:
                updated, err = update_aspirant_profile(
                    user_id=user_id,
                    full_name=f_name,
                    phone=f_phone,
                    district=d_dist,
                    state=d_state,
                    personal_data={"gender": f_gender, "dob": f_dob, "address": f_address},
                    professional_data={"education": f_edu, "skills": f_skills, "experience": f_exp, "certifications": f_certs},
                    business_data={"business_name": b_name, "business_type": b_type, "sector": b_sector, "stage": b_stage, "revenue": b_revenue, "employee_count": b_team, "description": b_desc},
                    demographics_data={"district": d_dist, "state": d_state, "founder_category": d_cat, "is_dpiit_recognized": d_dpiit, "is_startuptn_registered": d_startuptn, "is_women_led": d_women}
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
        st.markdown("<p style='color:#94a3b8; font-size:0.9rem;'>The living story of your venture. Every milestone, mentor session, and operational breakthrough is preserved here.</p>", unsafe_allow_html=True)

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
                actor_name = event.get("actor_name") or ("Aspirant" if actor_role == "aspirant" else "Mentor")
                ev_data = event.get("event_data", {})
                title = ev_data.get("title") or event.get("event_type")
                desc = ev_data.get("description", "")
                date_display = str(event.get("event_date", ""))[:10]

                # Role-specific styling
                badge_bg = "#6366f1" if actor_role == "aspirant" else "#10b981" if actor_role == "guide" else "#f59e0b" if actor_role == "sme" else "#ec4899" if actor_role == "admin" else "#64748b"

                col_time, col_body, col_del = st.columns([1.2, 5, 0.8])
                with col_time:
                    st.markdown(f"""
                    <div style="font-weight:700; color:#64748B; font-size:0.9rem;">{date_display}</div>
                    <span style="display:inline-block; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:10px; background:{badge_bg}; color:#ffffff; text-transform:uppercase;">{actor_role}</span>
                    """, unsafe_allow_html=True)
                with col_body:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:0.9rem 1.2rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                        <div style="font-weight:700; color:#0F172A; font-size:1.05rem;">{title}</div>
                        <div style="color:#334155; font-size:0.9rem; margin-top:0.3rem; line-height:1.5;">{desc}</div>
                        <div style="font-size:0.75rem; color:#64748B; margin-top:0.4rem;">Logged by: {actor_name} ({actor_role})</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    # Aspirants can delete only their own manual entries
                    if actor_role == "aspirant":
                        if st.button("🗑️", key=f"del_ev_{event['id']}", help="Delete this entry"):
                            soft_delete_event(event["id"], user_id, "aspirant")
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
            st.markdown("#### 🔬 Your Assigned Domain SME")
            if sme:
                s_p = sme.get("profile_data", {})
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #f59e0b; border-radius:14px; padding:1.5rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="font-size:1.3rem; font-weight:800; color:#0F172A;">{sme.get('full_name')}</div>
                    <div style="color:#D97706; font-size:0.85rem; font-weight:600; margin-bottom:0.75rem;">Subject Matter Expert</div>
                    <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Specialization:</strong> {s_p.get('expertise', 'GST, Compliance & Technical Advisory')}</p>
                    <p style="font-size:0.9rem; color:#334155; margin-bottom:4px;"><strong>Industry:</strong> {s_p.get('industry', 'Compliance')}</p>
                    <p style="font-size:0.85rem; color:#64748B; margin-top:0.75rem;"><em>"{s_p.get('bio', 'Assigned to provide specialized technical audit and compliance guidance.')}"</em></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No SME assigned yet. If you need specialized help in GST, FSSAI, or Patents, submit a request under 'Help'.")

    # ─────────────────────────────────────────────────────────────
    # TAB 5: SCHEME MATCHES
    # ─────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🏦 Scheme Intelligence & Fund Explorer")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Explore funding opportunities: Review customized algorithmic matches for your enterprise, or search the complete catalogue of 170 central, state, and private venture capital funds.</p>", unsafe_allow_html=True)

        matches = match_schemes_for_aspirant(user_id)
        sub_m1, sub_m2 = st.tabs([f"🎯 Matched For Your Venture ({len(matches)})", "🔍 Explore All 170 Schemes & Funds"])

        with sub_m1:
            if not matches:
                st.info("No direct matches found. Try filling out more details in 'My Profile' (sector, stage, district).")
            else:
                st.success(f"Identified **{len(matches)}** Potentially Eligible Schemes based on your sector, stage, and location profile!")
                for s in matches:
                    score = s["match_score"]
                    status_label = s["recommendation_status"]
                    score_color = "#10b981" if score >= 80 else "#f59e0b"

                    with st.expander(f"{s['name']} — {score}% Match ({status_label})"):
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                            <div>
                                <span style="font-size:0.8rem; color:#2563EB; font-weight:700; text-transform:uppercase;">{s.get('agency')}</span>
                                <h4 style="margin:0.2rem 0; color:#0F172A; font-weight:700;">{s['name']}</h4>
                            </div>
                            <div style="background:{score_color}; color:#ffffff; font-weight:900; font-size:1.05rem; padding:4px 14px; border-radius:12px;">
                                {score}%
                            </div>
                        </div>
                        <div style="font-size:0.9rem; color:#334155; margin-bottom:0.75rem; line-height:1.4;">{s.get('brief') or s.get('description')}</div>
                        """, unsafe_allow_html=True)

                        st.markdown("##### ✓ Why This Matched:")
                        for r in s.get("match_reasons", []):
                            st.markdown(f"- <span style='color:#059669;'>✓</span> **{r}**", unsafe_allow_html=True)

                        c_info1, c_info2 = st.columns(2)
                        with c_info1:
                            st.markdown(f"**Funding Amount:** `{s.get('amount', 'N/A')}`")
                            st.markdown(f"**Stage:** `{s.get('stage', 'N/A')}`")
                        with c_info2:
                            st.markdown(f"**Funding Type:** `{s.get('funding_type', 'Grant')}`")
                            if s.get("application_url"):
                                st.markdown(f"[Official Portal Link ↗]({s['application_url']})")

        with sub_m2:
            c_as1, c_as2, c_as3 = st.columns([2.5, 1.2, 1.2])
            with c_as1:
                asp_sc_search = st.text_input("Search All Schemes & Funds", placeholder="e.g. IndiaAI, DLI, Accel Atoms, TANSEED, NEEDS, PMEGP...", key="asp_all_sc_search")
            with c_as2:
                asp_sc_cat = st.selectbox("Capital Category", ["ALL", "Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"], key="asp_sc_cat")
            with c_as3:
                asp_sc_stage = st.selectbox("Target Stage", ["ALL", "Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"], key="asp_sc_stage")

            all_schemes = list_schemes(search=asp_sc_search, category=asp_sc_cat, stage=asp_sc_stage, active_only=True)
            st.markdown(f"**Showing {len(all_schemes)} active schemes matching filters:**")

            for s in all_schemes[:40]:
                cat_tag = s.get("category_type", "Govt")
                cat_bg = "#EFF6FF" if "Central" in cat_tag else "#F5F3FF" if "State" in cat_tag else "#FDF2F8"
                cat_fg = "#2563EB" if "Central" in cat_tag else "#7C3AED" if "State" in cat_tag else "#DB2777"
                funding_type = s.get("funding_type") or "Grant / Support"
                stage_tag = s.get("stage") or "All Stages"
                amount_str = s.get("amount") or "Guidelines specified"

                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.4rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                        <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:{cat_bg}; color:{cat_fg};">{cat_tag}</span>
                        <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:#F8FAFC; color:#475569; border:1px solid #E2E8F0;">{funding_type}</span>
                        <span style="font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:6px; background:#F8FAFC; color:#475569; border:1px solid #E2E8F0;">{stage_tag}</span>
                    </div>
                    <div style="font-size:1.15rem; font-weight:800; color:#0F172A; line-height:1.3;">{s['name']}</div>
                    <div style="font-size:0.85rem; color:#64748B; font-weight:600; margin-top:3px;">
                        Agency / Institution: <span style="color:#334155;">{s.get('agency') or 'Central / State Ministry'}</span>
                    </div>
                    <div style="color:#059669; font-weight:700; font-size:0.95rem; margin:0.5rem 0 0.4rem;">
                        💵 Funding Amount: {amount_str}
                    </div>
                    <div style="color:#334155; font-size:0.88rem; line-height:1.45; margin-bottom:0.6rem;">
                        {s.get('brief') or s.get('description') or 'Comprehensive capital support and mentorship.'}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:#64748B; padding-top:0.4rem; border-top:1px solid #F1F5F9;">
                        <div>📍 Geography / Scope: <strong>{s.get('state_scope', 'All India')}</strong></div>
                        <div>{f'<a href="{s["application_url"]}" target="_blank" style="color:#2563EB; font-weight:600; text-decoration:none;">Official Portal Link ↗</a>' if s.get("application_url") else ''}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # TAB 6: HELP / SUPPORT
    # ─────────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 💬 Ask for Help")
        st.markdown("<p style='color:#64748B; font-size:0.9rem;'>Need assistance with government registration, bank proposals, or technical mentoring? Submit a ticket below.</p>", unsafe_allow_html=True)

        with st.form("form_help"):
            h_subj = st.text_input("Subject", placeholder="e.g. GST Registration, Bank Proposal Review, PMEGP Quotations")
            col_hp1, col_hp2 = st.columns([3, 1])
            with col_hp1:
                h_msg = st.text_area("Message / Description", placeholder="Describe exactly what you need help with...")
            with col_hp2:
                h_prio = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "URGENT"], index=1)

            if st.form_submit_button("SEND HELP REQUEST", type="primary"):
                req, err = create_request(user_id, h_subj, h_msg, h_prio)
                if req:
                    st.success("Help request submitted! Admin has been notified.")
                    st.rerun()
                else:
                    st.error(err or "Failed to submit request.")

        st.markdown("#### Your Support History")
        my_reqs = list_requests(aspirant_id=user_id)
        if not my_reqs:
            st.info("No open help requests.")
        else:
            for r in my_reqs:
                st_color = "#f59e0b" if r["status"] == "OPEN" else "#3b82f6" if r["status"] == "IN_PROGRESS" else "#10b981"
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1rem; margin-bottom:0.75rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#0F172A; font-size:1rem;">{r['subject']}</strong>
                        <span style="background:{st_color}; color:#ffffff; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:6px;">{r['status']}</span>
                    </div>
                    <div style="color:#334155; font-size:0.88rem; margin:0.4rem 0;">{r['message']}</div>
                    {f'<div style="background:#F0FDF4; border-left:3px solid #10b981; border:1px solid #BBF7D0; padding:0.5rem 0.75rem; border-radius:0 6px 6px 0; font-size:0.85rem; color:#166534; margin-top:0.5rem;"><strong>Admin Response:</strong> {r["admin_response"]}</div>' if r.get('admin_response') else ''}
                </div>
                """, unsafe_allow_html=True)
