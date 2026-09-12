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


def to_multiline_str(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return "\n".join(str(x) for x in val if str(x).strip())
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    return "\n".join(str(x) for x in parsed if str(x).strip())
            except Exception:
                pass
        return val_s
    return str(val)

def to_comma_str(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return ", ".join(str(x) for x in val if str(x).strip())
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    return ", ".join(str(x) for x in parsed if str(x).strip())
            except Exception:
                pass
        return val_s
    return str(val)

# ─────────────────────────────────────────────────────────────────────────────
# SPACIOUS FULL-FEATURED MODAL DIALOGS (STREAMLIT >= 1.34)
# ─────────────────────────────────────────────────────────────────────────────
if hasattr(st, "dialog"):
    _dialog_decorator = st.dialog
else:
    def _dialog_decorator(title=None, width="small"):
        def wrapper(func):
            return func
        return wrapper

@_dialog_decorator("✏️ Edit Funding Scheme & Intelligence", width="large")
def open_edit_scheme_dialog(s: dict, admin_id: str = None):
    sid = s.get("id") or s.get("source_id", "SCH-GEN")
    name = s.get("name", "Untitled Scheme")
    agency = s.get("agency", "")

    st.markdown(f"""
    <div style="background:#1E293B; border-left:4px solid #8B5CF6; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
        <div style="font-size:1.15rem; font-weight:800; color:#FFFFFF;">{html.escape(name)}</div>
        <div style="font-size:0.84rem; color:#94A3B8; margin-top:4px;">
            Agency / Institution: <strong style="color:#CBD5E1;">{html.escape(agency or 'N/A')}</strong> &nbsp;|&nbsp;
            ID: <code style="color:#A78BFA; background:#0F172A; padding:2px 7px; border-radius:4px; font-weight:600;">{html.escape(sid)}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(f"dialog_edit_form_{sid}"):
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 1. Core Parameters & Capital",
            "🏢 2. Sectors & Description",
            "⚖️ 3. Eligibility & Terms",
            "💡 4. Insider Intel, Red Flags & Copilot"
        ])

        with tab1:
            ed_name = st.text_input("Scheme / Fund Name *", value=name)

            c1, c2 = st.columns(2)
            with c1:
                ed_agency = st.text_input("Agency / Ministry / Firm *", value=agency)
                ed_amount = st.text_input("Funding Amount & Nature *", value=s.get("amount", ""))
                ed_type = st.text_input("Funding / Capital Type (e.g. Grant, Equity, Debt, Subsidy)", value=s.get("funding_type") or s.get("scheme_type") or "Grant")

            with c2:
                cat_options = ["Central Govt", "State Govt", "Private VC / Angel", "Foreign / Global"]
                current_cat = s.get("category_type") or "Central Govt"
                cat_idx = 0
                for idx, opt in enumerate(cat_options):
                    if opt.lower() in current_cat.lower():
                        cat_idx = idx
                        break
                ed_cat = st.selectbox("Category Type", cat_options, index=cat_idx)

                stage_options = ["Ideation / R&D", "Pre-Seed / Seed", "Pre-Series A / Series A", "Growth / Debt Scaling"]
                current_stage = s.get("stage") or "All Stages"
                stage_idx = 1
                for idx, opt in enumerate(stage_options):
                    if opt.lower() in current_stage.lower():
                        stage_idx = idx
                        break
                ed_stage = st.selectbox("Target Startup Stage", stage_options, index=stage_idx)

                scope_options = ["All India", "Tamil Nadu", "Regional / Global"]
                current_scope = s.get("state_scope") or s.get("geography") or "All India"
                scope_idx = 1 if "Tamil" in current_scope else 0
                ed_scope = st.selectbox("Geographic Scope", scope_options, index=scope_idx)

            c3, c4 = st.columns(2)
            with c3:
                ed_url = st.text_input("Official Application / Nodal Portal URL", value=s.get("application_url", ""))
            with c4:
                ed_verified = st.text_input("Last Verified Note", value=s.get("last_verified") or "August 2026")

        with tab2:
            sec_str = to_comma_str(s.get("sectors")) or "General, AI, DeepTech"
            ed_sectors = st.text_input("Eligible Sectors (comma-separated)", value=sec_str, help="e.g. Food Processing, DeepTech, Agritech, SaaS, HealthTech")
            ed_brief = st.text_input("Executive One-Line Summary Brief", value=s.get("brief") or s.get("description", "")[:200])
            ed_desc = st.text_area("Full Scheme Scope & Operational Details", value=s.get("description", ""), height=150)

        with tab3:
            c_e1, c_e2 = st.columns(2)
            with c_e1:
                elig_str = to_multiline_str(s.get("eligibility"))
                ed_elig = st.text_area("Eligibility Criteria (One point per line)", value=elig_str, height=150, help="Specify DPIIT, turnover, years in operation, or founding requirements.")
            with c_e2:
                terms_str = to_multiline_str(s.get("terms"))
                ed_terms = st.text_area("Sanction Terms & Financial Conditions (One point per line)", value=terms_str, height=150, help="Specify milestone tranches, matching equity, interest rates, or reporting.")

        with tab4:
            st.markdown("<p style='font-size:0.84rem; color:#94A3B8; margin-bottom:8px;'>Add insider nuances, hidden agenda requirements, critical pitfalls, and pre-engineered AI prompt templates.</p>", unsafe_allow_html=True)
            c_i1, c_i2 = st.columns(2)
            with c_i1:
                agenda_str = to_multiline_str(s.get("hidden_agenda"))
                ed_agenda = st.text_area("🤫 Insider Intelligence / Hidden Agenda (One point per line)", value=agenda_str, height=130, help="Insider evaluation priorities used by government or VC committees.")
            with c_i2:
                flags_str = to_multiline_str(s.get("red_flags"))
                ed_flags = st.text_area("⚠️ Red Flags & Traps to Avoid (One point per line)", value=flags_str, height=130, help="Common traps, compliance disqualifiers, or equity conditions.")

            prompt_str = s.get("application_prompt") or f"""ROLE: Senior Startup Funding & VC Consultant
TARGET FUND: {name} ({agency})
FUND TYPE: {s.get('funding_type') or 'Grant'}

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
            ed_prompt = st.text_area("🤖 AI Copilot Application Prompt Template", value=prompt_str, height=160, help="Prompt template founders can copy into AI Copilot to generate DPR proposals.")

        c_sub1, c_sub2 = st.columns([1.5, 1])
        with c_sub1:
            saved = st.form_submit_button("💾 Save All Scheme Updates", type="primary", use_container_width=True)
        with c_sub2:
            cancelled = st.form_submit_button("Cancel / Discard", use_container_width=True)

        if saved:
            if not ed_name.strip() or not ed_agency.strip():
                st.error("Scheme Name and Agency are required.")
            else:
                new_sectors = [x.strip() for x in ed_sectors.split(",") if x.strip()]
                new_elig = [x.strip() for x in ed_elig.split("\n") if x.strip()]
                new_terms = [x.strip() for x in ed_terms.split("\n") if x.strip()]
                new_agenda = [x.strip() for x in ed_agenda.split("\n") if x.strip()]
                new_flags = [x.strip() for x in ed_flags.split("\n") if x.strip()]

                is_active = bool(s.get("is_active", True))
                updated_scheme = {
                    "id": sid,
                    "name": ed_name.strip(),
                    "agency": ed_agency.strip(),
                    "amount": ed_amount.strip(),
                    "funding_type": ed_type.strip(),
                    "scheme_type": ed_type.strip(),
                    "category_type": ed_cat,
                    "stage": ed_stage,
                    "state_scope": ed_scope,
                    "geography": "State" if "Tamil" in ed_scope else "National",
                    "application_url": ed_url.strip(),
                    "last_verified": ed_verified.strip(),
                    "brief": ed_brief.strip(),
                    "description": ed_desc.strip(),
                    "sectors": new_sectors,
                    "eligibility": new_elig,
                    "terms": new_terms,
                    "hidden_agenda": new_agenda,
                    "red_flags": new_flags,
                    "application_prompt": ed_prompt.strip(),
                    "is_active": is_active,
                    "status": "active" if is_active else "archived"
                }
                upsert_scheme(updated_scheme, admin_id or "admin")
                st.success(f"Successfully saved updates to '{ed_name}'!")
                st.rerun()

        if cancelled:
            st.rerun()

@_dialog_decorator("🗑️ Confirm Scheme Deletion", width="small")
def open_delete_scheme_dialog(s: dict, admin_id: str = None):
    sid = s.get("id") or s.get("source_id", "SCH-GEN")
    name = s.get("name", "Untitled Scheme")
    st.error(f"Are you sure you want to permanently delete **{name}**?")
    st.markdown(f"<p style='color:#64748B; font-size:0.85rem;'>Scheme ID: <code>{html.escape(sid)}</code>.<br>This will permanently delete this funding opportunity from both local and cloud databases. This action cannot be undone.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Yes, Delete", type="primary", use_container_width=True):
            delete_scheme(sid, admin_id or "admin")
            st.success(f"Deleted '{name}'")
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

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

    # If Admin, Render Clean Action Buttons (Edit Modal Dialog, Archive, Delete Modal Dialog)
    if is_admin:
        c_act1, c_act2, c_act3 = st.columns([1, 1, 1])

        # 1. Full Edit Modal Dialog
        with c_act1:
            if st.button("✏️ Edit Scheme", key=f"{key_prefix}_edit_{sid}", use_container_width=True, help="Open spacious modal scheme editor"):
                open_edit_scheme_dialog(s, admin_id)

        # 2. Archive / Activate Toggle
        with c_act2:
            action_label = "📦 Archive" if is_active else "🚀 Activate"
            if st.button(action_label, key=f"{key_prefix}_arch_{sid}", use_container_width=True):
                toggle_archive_scheme(sid, admin_id or "admin")
                st.rerun()

        # 3. Permanent Delete Modal Dialog
        with c_act3:
            if st.button("🗑️ Delete", key=f"{key_prefix}_del_{sid}", use_container_width=True, help="Permanently delete this scheme"):
                open_delete_scheme_dialog(s, admin_id)

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
