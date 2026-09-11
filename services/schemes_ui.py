"""
services/schemes_ui.py — Fund Explorer UI Component matching FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html
================================================================================================
Renders funding schemes with 100% fidelity to the Founder AI Digital Playbook 2026 Fund Explorer:
- Title, Agency, Category & Type tags
- Funding Amount callout
- Details / Brief description
- Sector pills & Geography tag
- 🤫 Insider Intelligence / Hidden Agenda callout (Amber)
- ⚠️ Red Flags / Warnings callout (Red)
- 🤖 AI Pitch & Application Prompt expander with 1-click copy code block
- Official Portal Link & Last Verified badge
- Full Admin CRUD controls (Edit all 24 fields, Archive/Activate, Delete with confirmation)
"""

import streamlit as st
import json
from services.schemes import upsert_scheme, toggle_archive_scheme, delete_scheme

def parse_list_field(val, default="None"):
    if not val:
        return default
    if isinstance(val, list):
        return "<br>".join(f"• {item}" if not item.startswith((">>", "!!", "•")) else item for item in val)
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    return "<br>".join(f"• {item}" if not str(item).startswith((">>", "!!", "•")) else str(item) for item in parsed)
            except Exception:
                pass
        # Fallback: split by newlines if any
        lines = [l.strip() for l in val_s.split("\n") if l.strip()]
        if len(lines) > 1:
            return "<br>".join(f"• {line}" if not line.startswith((">>", "!!", "•")) else line for line in lines)
        return val_s
    return str(val)

def parse_sectors_list(val):
    if not val:
        return ["All Sectors"]
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return [s.strip() for s in val_s.split(",") if s.strip()]
    return ["All Sectors"]

def render_fund_explorer_card(s: dict, is_admin: bool = False, admin_id: str = None, key_prefix: str = "fe"):
    sid = s.get("id") or s.get("source_id", "SCH-GEN")
    name = s.get("name", "Untitled Scheme")
    agency = s.get("agency", "Government / Syndicate")
    amount = s.get("amount") or "Grant / Equity Support"
    details = s.get("brief") or s.get("description") or "Comprehensive venture capital and grant support."
    
    cat_type = s.get("category_type") or "Central Govt"
    fund_type = s.get("funding_type") or s.get("scheme_type") or "Grant"
    stage_tag = s.get("stage") or "All Stages"
    scope_str = s.get("state_scope") or s.get("geography") or "All India"
    last_verified = s.get("last_verified") or "August 2026"
    app_url = s.get("application_url") or ""
    
    is_active = bool(s.get("is_active", True))
    status_tag = "ACTIVE" if is_active else "ARCHIVED"
    status_bg = "#ECFDF5" if is_active else "#F1F5F9"
    status_fg = "#059669" if is_active else "#64748B"
    status_border = "#A7F3D0" if is_active else "#CBD5E1"
    
    cat_bg = "#EFF6FF" if "Central" in cat_type else "#F5F3FF" if "State" in cat_type else "#FDF2F8"
    cat_fg = "#2563EB" if "Central" in cat_type else "#7C3AED" if "State" in cat_type else "#DB2777"
    cat_border = "#BFDBFE" if "Central" in cat_type else "#DDD6FE" if "State" in cat_type else "#FBCFE8"

    sectors = parse_sectors_list(s.get("sectors"))
    sectors_html = "".join([f'<span style="display:inline-block; font-size:0.75rem; font-weight:600; padding:2px 8px; border-radius:6px; background:#F1F5F9; color:#334155; border:1px solid #E2E8F0; margin-right:6px; margin-bottom:4px;">{sec}</span>' for sec in sectors])
    
    agenda_text = parse_list_field(s.get("hidden_agenda"), default=">> Emphasize local job creation, import substitution & revenue growth.")
    flag_text = parse_list_field(s.get("red_flags"), default="!! Verify official sanction terms, audit rules & equity rights before signing.")
    
    app_prompt_text = s.get("application_prompt") or f"""ROLE: Senior Startup Funding & VC Consultant
TARGET FUND: {name} ({agency})
FUND TYPE: {fund_type}

BUSINESS CONTEXT:
Company Name: [INSERT_COMPANY_NAME]
Industry / Sector: [INSERT_PRIMARY_SECTOR]
Startup Stage: [INSERT_STARTUP_STAGE]
Requested Amount: [INSERT_REQUESTED_AMOUNT]

EVIDENCE & DOCUMENTS ATTACHED:
I have uploaded: Certificate of Incorporation, DPIIT Certificate, Pitch Deck / DPR, Udyam Registration, Cap Table.

TASK:
1. Draft a compelling 1-page Executive Project Proposal for {name} highlighting innovation, market impact, and employment generation.
2. Formulate a transparent Fund Utilization Table matching official expenditure guidelines.
3. Address key scheme eligibility criteria.
4. List key milestone deliverables and timeline required for tranche disbursement.

CONSTRAINTS: Adhere strictly to official eligibility criteria. Do not exaggerate revenue.
OUTPUT FORMAT: 1-Page Executive Proposal + Budget Allocation Table + Milestone Schedule."""

    # Outer Container Card
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:4px solid #2563EB; border-radius:12px; padding:1.4rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <!-- Top Row: Title, Agency, Badges -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:0.75rem;">
            <div style="flex:1; min-width:280px;">
                <h3 style="font-size:1.25rem; color:#0F172A; font-weight:800; margin:0 0 4px 0; line-height:1.3;">{name}</h3>
                <p style="color:#64748B; font-size:0.88rem; margin:0;">
                    <strong style="color:#334155;">Agency / Institution:</strong> {agency}
                </p>
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
                <span style="font-size:0.75rem; font-weight:700; padding:3px 10px; border-radius:8px; background:{cat_bg}; color:{cat_fg}; border:1px solid {cat_border};">{cat_type}</span>
                <span style="font-size:0.75rem; font-weight:700; padding:3px 10px; border-radius:8px; background:#F8FAFC; color:#475569; border:1px solid #CBD5E1;">{fund_type}</span>
                <span style="font-size:0.75rem; font-weight:700; padding:3px 10px; border-radius:8px; background:#F8FAFC; color:#475569; border:1px solid #CBD5E1;">{stage_tag}</span>
                {f'<span style="font-size:0.75rem; font-weight:700; padding:3px 10px; border-radius:8px; background:{status_bg}; color:{status_fg}; border:1px solid {status_border};">{status_tag}</span>' if is_admin else ''}
            </div>
        </div>

        <!-- Funding Amount Callout -->
        <div style="font-size:1rem; color:#059669; font-weight:800; margin-bottom:0.6rem;">
            💵 Funding Amount: {amount}
        </div>

        <!-- Brief / Details -->
        <div style="font-size:0.9rem; color:#334155; line-height:1.5; margin-bottom:0.85rem;">
            {details}
        </div>

        <!-- Sectors & Scope Badges -->
        <div style="margin-bottom:0.85rem;">
            {sectors_html}
            <span style="display:inline-block; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:6px; background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;">📍 {scope_str}</span>
        </div>

        <!-- 🤫 INSIDER INTELLIGENCE / HIDDEN AGENDA (Amber Callout) -->
        <div style="background:#FFFBEB; border-left:4px solid #F59E0B; border:1px solid #FDE68A; border-left-width:4px; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#92400E; margin-bottom:0.75rem; line-height:1.45;">
            <div style="font-weight:800; color:#B45309; margin-bottom:4px;">🤫 INSIDER INTELLIGENCE / HIDDEN AGENDA:</div>
            <div>{agenda_text}</div>
        </div>

        <!-- ⚠️ RED FLAGS / WARNINGS (Red Callout) -->
        <div style="background:#FEF2F2; border-left:4px solid #EF4444; border:1px solid #FECACA; border-left-width:4px; padding:0.85rem 1rem; border-radius:0 8px 8px 0; font-size:0.86rem; color:#991B1B; margin-bottom:0.85rem; line-height:1.45;">
            <div style="font-weight:800; color:#DC2626; margin-bottom:4px;">⚠️ RED FLAGS / WARNINGS:</div>
            <div>{flag_text}</div>
        </div>

        <!-- Official Portal & Verification Row -->
        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:0.6rem; border-top:1px solid #F1F5F9; font-size:0.82rem; color:#64748B;">
            <div>
                {f'<a href="{app_url}" target="_blank" style="color:#2563EB; font-weight:700; text-decoration:none;">Official Portal Link &nearr;</a>' if app_url else '<span style="color:#94A3B8;">Direct Nodal Portal Submission</span>'}
            </div>
            <div>
                Verified: <strong style="color:#475569;">{last_verified}</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Collapsible AI Pitch & Application Prompt Box
    with st.expander(f"🤖 View AI Pitch & Application Prompt for '{name}'", expanded=False):
        st.markdown("<p style='font-size:0.82rem; color:#64748B; margin-bottom:6px;'>Copy this prompt into Claude, ChatGPT, or your AI Copilot to generate a 1-page DPR and official application proposal:</p>", unsafe_allow_html=True)
        st.code(app_prompt_text, language="markdown")

    # If Admin, Render Complete CRUD Actions
    if is_admin:
        c_act1, c_act2, c_act3 = st.columns([2.5, 1.2, 1.2])

        # 1. Full Edit Form Expander
        with c_act1:
            with st.expander(f"✏️ Edit '{name}' (Full Data Fields)"):
                with st.form(f"{key_prefix}_edit_form_{sid}"):
                    st.markdown("##### Basic Information")
                    c_e1, c_e2 = st.columns(2)
                    with c_e1:
                        ed_name = st.text_input("Scheme / Fund Name", value=name)
                        ed_agency = st.text_input("Agency / Ministry / Firm", value=agency)
                        ed_amount = st.text_input("Funding Amount & Nature", value=amount)
                        ed_type = st.text_input("Funding / Capital Type", value=fund_type)
                    with c_e2:
                        cat_options = ["Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"]
                        cat_idx = 0
                        for idx, opt in enumerate(cat_options):
                            if opt.lower() in cat_type.lower():
                                cat_idx = idx
                                break
                        ed_cat = st.selectbox("Category", cat_options, index=cat_idx)

                        stage_options = ["Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"]
                        stage_idx = 1
                        for idx, opt in enumerate(stage_options):
                            if opt.lower() in stage_tag.lower():
                                stage_idx = idx
                                break
                        ed_stage = st.selectbox("Target Stage", stage_options, index=stage_idx)

                        scope_options = ["All India", "Tamil Nadu", "Regional / Global"]
                        scope_idx = 1 if "Tamil" in scope_str else 0
                        ed_scope = st.selectbox("Geographic Scope", scope_options, index=scope_idx)
                        ed_url = st.text_input("Official Application URL", value=app_url)

                    st.markdown("##### Sectors & Descriptions")
                    sectors_raw = s.get("sectors")
                    if isinstance(sectors_raw, list):
                        sec_str = ", ".join(sectors_raw)
                    elif isinstance(sectors_raw, str) and sectors_raw.startswith("["):
                        try:
                            sec_str = ", ".join(json.loads(sectors_raw))
                        except Exception:
                            sec_str = sectors_raw
                    else:
                        sec_str = str(sectors_raw or "General, AI, DeepTech")

                    ed_sectors = st.text_input("Eligible Sectors (comma-separated)", value=sec_str)
                    ed_brief = st.text_input("One-line Brief", value=s.get("brief") or details[:200])
                    ed_desc = st.text_area("Full Description / Details", value=s.get("description") or details, height=90)

                    st.markdown("##### Intelligence, Red Flags & AI Prompt")
                    # Format existing list fields for editing
                    agenda_val = s.get("hidden_agenda")
                    if isinstance(agenda_val, list):
                        agenda_str = "\n".join(agenda_val)
                    elif isinstance(agenda_val, str) and agenda_val.startswith("["):
                        try:
                            agenda_str = "\n".join(json.loads(agenda_val))
                        except Exception:
                            agenda_str = agenda_val
                    else:
                        agenda_str = str(agenda_val or "")

                    flags_val = s.get("red_flags")
                    if isinstance(flags_val, list):
                        flags_str = "\n".join(flags_val)
                    elif isinstance(flags_val, str) and flags_val.startswith("["):
                        try:
                            flags_str = "\n".join(json.loads(flags_val))
                        except Exception:
                            flags_str = flags_val
                    else:
                        flags_str = str(flags_val or "")

                    ed_agenda = st.text_area("Insider Intelligence / Hidden Agenda (One point per line)", value=agenda_str, height=90)
                    ed_flags = st.text_area("Red Flags / Warnings (One point per line)", value=flags_str, height=90)
                    ed_prompt = st.text_area("AI Pitch & Application Prompt", value=app_prompt_text, height=130)

                    if st.form_submit_button("SAVE SCHEME UPDATES", type="primary"):
                        # Parse sectors
                        new_sectors = [x.strip() for x in ed_sectors.split(",") if x.strip()]
                        new_agenda = [x.strip() for x in ed_agenda.split("\n") if x.strip()]
                        new_flags = [x.strip() for x in ed_flags.split("\n") if x.strip()]

                        updated_scheme = {
                            "id": sid,
                            "name": ed_name,
                            "agency": ed_agency,
                            "amount": ed_amount,
                            "funding_type": ed_type,
                            "category_type": ed_cat,
                            "stage": ed_stage,
                            "state_scope": ed_scope,
                            "application_url": ed_url,
                            "brief": ed_brief,
                            "description": ed_desc,
                            "sectors": new_sectors,
                            "hidden_agenda": new_agenda,
                            "red_flags": new_flags,
                            "application_prompt": ed_prompt,
                            "is_active": is_active,
                            "status": "active" if is_active else "archived"
                        }
                        upsert_scheme(updated_scheme, admin_id or "admin")
                        st.success(f"Saved updates to '{ed_name}'!")
                        st.rerun()

        # 2. Archive / Activate Toggle
        with c_act2:
            action_label = "📦 Archive" if is_active else "🚀 Activate"
            if st.button(action_label, key=f"{key_prefix}_arch_{sid}", use_container_width=True):
                toggle_archive_scheme(sid, admin_id or "admin")
                st.rerun()

        # 3. Permanent Delete
        with c_act3:
            del_key = f"{key_prefix}_confirm_del_{sid}"
            if st.button("🗑️ Delete", key=f"{key_prefix}_del_{sid}", help="Permanently delete this scheme", use_container_width=True):
                st.session_state[del_key] = True

            if st.session_state.get(del_key):
                st.warning(f"Delete '{name}'?")
                cd1, cd2 = st.columns(2)
                with cd1:
                    if st.button("CONFIRM", key=f"{key_prefix}_yes_{sid}", type="primary"):
                        delete_scheme(sid, admin_id or "admin")
                        st.session_state.pop(del_key, None)
                        st.success(f"Deleted '{name}'!")
                        st.rerun()
                with cd2:
                    if st.button("CANCEL", key=f"{key_prefix}_no_{sid}"):
                        st.session_state.pop(del_key, None)
                        st.rerun()

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
