"""
services/schemes_ui.py — Fund Explorer Card Component matching FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html
====================================================================================================
Renders funding schemes with 100% visual fidelity to the Founder AI Digital Playbook 2026 Fund Explorer:
- Obsidian-violet dark card container with 1.5px radiant purple border (#8B5CF6)
- High-contrast white scheme name (#FFFFFF, 1.22rem)
- Agency / Ministry attribution (#94A3B8)
- Capital type capsule pill with purple glow and category badge
- Neon emerald funding amount callout (#34D399)
- Description / Brief (#CBD5E1)
- Sectors tags row (#1E293B capsules) and Geographic Scope tag
- 🤫 Insider Intelligence / Hidden Agenda amber box (#F59E0B left border, #FCD34D text)
- ⚠️ Red Flags / Warnings red box (#EF4444 left border, #FCA5A5 text)
- 🤖 Collapsible AI Pitch & Application Prompt expander with copyable code block
- Official Portal Link & Last Verified footer
- Full Admin CRUD actions: Edit all 24 fields in-place, Archive/Activate toggle, Delete with confirmation
"""

import streamlit as st
import json
import html
from services.schemes import upsert_scheme, toggle_archive_scheme, delete_scheme

def parse_list_field(val, default="None"):
    if not val:
        return default
    if isinstance(val, list):
        items = [str(x) for x in val if x]
        return "<br>".join(f"• {html.escape(item)}" if not item.startswith((">>", "!!", "•")) else html.escape(item) for item in items)
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    items = [str(x) for x in parsed if x]
                    return "<br>".join(f"• {html.escape(item)}" if not item.startswith((">>", "!!", "•")) else html.escape(item) for item in items)
            except Exception:
                pass
        lines = [l.strip() for l in val_s.split("\n") if l.strip()]
        if len(lines) > 1:
            return "<br>".join(f"• {html.escape(line)}" if not line.startswith((">>", "!!", "•")) else html.escape(line) for line in lines)
        return html.escape(val_s)
    return html.escape(str(val))

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
    status_bg = "rgba(16, 185, 129, 0.2)" if is_active else "rgba(148, 163, 184, 0.2)"
    status_fg = "#34D399" if is_active else "#94A3B8"
    status_border = "#059669" if is_active else "#64748B"

    sectors = parse_sectors_list(s.get("sectors"))
    sectors_html = "".join([
        f'<span style="display:inline-block; font-size:0.7rem; font-weight:700; text-transform:uppercase; padding:3px 9px; border-radius:9999px; background:#1E293B; color:#E2E8F0; border:1px solid #334155; margin-right:5px; margin-bottom:5px;">{html.escape(str(sec))}</span>'
        for sec in sectors
    ])
    
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

    portal_link_html = f'<a href="{app_url}" target="_blank" style="color:#A78BFA; font-weight:700; text-decoration:none; font-size:0.82rem;">Official Portal Link &nearr;</a>' if app_url else '<span style="color:#64748B; font-size:0.82rem;">Direct Nodal Portal Submission</span>'

    # Build status badge HTML (admin only)
    status_badge = f'<span style="display:inline-block;font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:9999px;background:{status_bg};color:{status_fg};border:1px solid {status_border};">{status_tag}</span>' if is_admin else ''

    # Outer Container Card matching Playbook Fund Explorer
    st.markdown(f"""<div style="background:#11131F;border:1.5px solid #8B5CF6;border-radius:14px;padding:1.25rem;margin-bottom:0.75rem;box-shadow:0 4px 20px rgba(139,92,246,0.12);">
<div style="margin-bottom:0.6rem;">
<div style="font-size:1.15rem;color:#FFFFFF;font-weight:800;line-height:1.3;margin:0 0 5px 0;">{html.escape(name)}</div>
<div style="color:#94A3B8;font-size:0.84rem;margin:0;line-height:1.35;"><strong style="color:#CBD5E1;">Agency / Institution:</strong> {html.escape(agency)}</div>
</div>
<div style="margin-bottom:0.75rem;display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
<span style="display:inline-block;font-size:0.68rem;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;padding:3px 10px;border-radius:9999px;background:rgba(139,92,246,0.22);color:#C4B5FD;border:1px solid #8B5CF6;">{html.escape(fund_type)}</span>
<span style="display:inline-block;font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:9999px;background:rgba(59,130,246,0.15);color:#93C5FD;border:1px solid #3B82F6;">{html.escape(cat_type)}</span>
{status_badge}
</div>
<div style="font-size:0.95rem;color:#34D399;font-weight:700;margin-bottom:0.65rem;line-height:1.35;">Funding: {html.escape(amount)}</div>
<div style="font-size:0.84rem;color:#CBD5E1;line-height:1.45;margin-bottom:0.85rem;">{html.escape(details[:250])}</div>
<div style="margin-bottom:0.85rem;">{sectors_html}
<span style="display:inline-block;font-size:0.7rem;font-weight:700;text-transform:uppercase;padding:3px 9px;border-radius:9999px;background:rgba(16,185,129,0.15);color:#34D399;border:1px solid #059669;margin-bottom:5px;">{html.escape(scope_str)}</span>
</div>
<div style="background:rgba(245,158,11,0.12);border-left:4px solid #F59E0B;padding:0.75rem 0.9rem;border-radius:0 8px 8px 0;font-size:0.82rem;color:#FCD34D;line-height:1.45;margin-bottom:0.65rem;">
<div style="font-weight:800;color:#FBBF24;margin-bottom:3px;font-size:0.84rem;">INSIDER INTELLIGENCE:</div>
<div>{agenda_text}</div>
</div>
<div style="background:rgba(239,68,68,0.12);border-left:4px solid #EF4444;padding:0.75rem 0.9rem;border-radius:0 8px 8px 0;font-size:0.82rem;color:#FCA5A5;line-height:1.45;margin-bottom:0.75rem;">
<div style="font-weight:800;color:#F87171;margin-bottom:3px;font-size:0.84rem;">RED FLAGS:</div>
<div>{flag_text}</div>
</div>
<div style="display:flex;justify-content:space-between;align-items:center;padding-top:0.6rem;border-top:1px solid rgba(255,255,255,0.08);font-size:0.8rem;color:#94A3B8;margin-top:0.4rem;">
<div>{portal_link_html}</div>
<div>Verified: <strong style="color:#E2E8F0;">{html.escape(last_verified)}</strong></div>
</div>
</div>""", unsafe_allow_html=True)

    # Collapsible AI Pitch & Application Prompt Box
    with st.expander("🤖 AI Pitch Prompt", expanded=False):
        st.markdown("<p style='font-size:0.82rem; color:#64748B; margin-bottom:6px;'>Copy this prompt into Claude, ChatGPT, or your AI Copilot to generate a 1-page DPR and official application proposal:</p>", unsafe_allow_html=True)
        st.code(app_prompt_text, language="markdown")

    # If Admin, Render Complete CRUD Actions
    if is_admin:
        c_act1, c_act2, c_act3 = st.columns([1.4, 0.9, 0.9])

        # 1. Full Edit Form Expander
        with c_act1:
            with st.expander("✏️ Edit Scheme"):
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
                    ed_desc = st.text_area("Full Description / Details", value=s.get("description") or details, height=80)

                    st.markdown("##### Intelligence, Red Flags & AI Prompt")
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

                    ed_agenda = st.text_area("Insider Intelligence / Hidden Agenda (One point per line)", value=agenda_str, height=80)
                    ed_flags = st.text_area("Red Flags / Warnings (One point per line)", value=flags_str, height=80)
                    ed_prompt = st.text_area("AI Pitch & Application Prompt", value=app_prompt_text, height=120)

                    if st.form_submit_button("SAVE SCHEME UPDATES", type="primary"):
                        new_sectors = [x.strip() for x in ed_sectors.split(",") if x.strip()]
                        new_agenda = [x.strip() for x in ed_agenda.split("\n") if x.strip()]
                        new_flags = [x.strip() for x in ed_flags.split("\n") if x.strip()]

                        updated_scheme = {
                            "id": sid,
                            "name": ed_name,
                            "agency": ed_agency,
                            "amount": ed_amount,
                            "funding_type": ed_type,
                            "scheme_type": ed_type,
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
