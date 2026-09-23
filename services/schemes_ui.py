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
from services.constants import (
    MASTER_SECTORS,
    MASTER_STAGES,
    MASTER_FUNDING_TYPES,
    MASTER_CATEGORY_TYPES,
    MASTER_GEOGRAPHIC_SCOPES,
    resolve_field_choice,
    _safe_esc
)

def _format_list_item(item: str) -> str:
    s = str(item).strip()
    if s.startswith(">>"):
        content = _safe_esc(s[2:].strip())
        return f'<div style="margin-bottom:4px;"><span style="color:#F59E0B !important; font-weight:900; font-size:0.95rem;">&#9654;</span> <span style="font-weight:600; color:inherit !important;">{content}</span></div>'
    elif s.startswith("!!"):
        content = _safe_esc(s[2:].strip())
        return f'<div style="margin-bottom:4px;"><span style="color:#EF4444 !important; font-weight:900; font-size:0.95rem;">&#9888;</span> <span style="font-weight:600; color:inherit !important;">{content}</span></div>'
    elif s.startswith("•"):
        content = _safe_esc(s[1:].strip())
        return f'<div style="margin-bottom:4px;"><span style="color:#94A3B8 !important; font-weight:800;">&bull;</span> <span style="font-weight:600; color:inherit !important;">{content}</span></div>'
    else:
        content = _safe_esc(s)
        return f'<div style="margin-bottom:4px;"><span style="color:#94A3B8 !important; font-weight:800;">&bull;</span> <span style="font-weight:600; color:inherit !important;">{content}</span></div>'

def parse_list_field(val, default="None"):
    if not val:
        return _format_list_item(default)
    if isinstance(val, list):
        items = [str(x) for x in val if x]
        return "".join(_format_list_item(item) for item in items)
    if isinstance(val, str):
        val_s = val.strip()
        if val_s.startswith("[") and val_s.endswith("]"):
            try:
                parsed = json.loads(val_s)
                if isinstance(parsed, list):
                    items = [str(x) for x in parsed if x]
                    return "".join(_format_list_item(item) for item in items)
            except Exception:
                pass
        lines = [l.strip() for l in val_s.split("\n") if l.strip()]
        if len(lines) > 1:
            return "".join(_format_list_item(line) for line in lines)
        return _format_list_item(val_s)
    return _format_list_item(str(val))

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
        <div style="font-size:1.15rem; font-weight:800; color:#FFFFFF;">{_safe_esc(name, default='Untitled Scheme')}</div>
        <div style="font-size:0.84rem; color:#94A3B8; margin-top:4px;">
            Agency / Institution: <strong style="color:#CBD5E1;">{_safe_esc(agency, default='N/A')}</strong> &nbsp;|&nbsp;
            ID: <code style="color:#A78BFA; background:#0F172A; padding:2px 7px; border-radius:4px; font-weight:600;">{_safe_esc(sid)}</code>
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
                cur_ftype = s.get("funding_type") or s.get("scheme_type") or "Grant"
                ftype_idx, ftype_custom = resolve_field_choice(cur_ftype, MASTER_FUNDING_TYPES, "Other / Blended Capital (Specify)")
                ed_type_sel = st.selectbox("Funding / Capital Type", MASTER_FUNDING_TYPES, index=ftype_idx, key=f"{sid}_sel_ftype")
                ed_type = ed_type_sel
                if ed_type_sel == "Other / Blended Capital (Specify)":
                    ed_type_custom = st.text_input("Specify Capital Type *", value=ftype_custom, placeholder="e.g. Revenue Share, SAFE", key=f"{sid}_custom_ftype")
                    if ed_type_custom and ed_type_custom.strip():
                        ed_type = ed_type_custom.strip()

            with c2:
                cur_cat = s.get("category_type") or "Central Govt"
                cat_idx, cat_custom = resolve_field_choice(cur_cat, MASTER_CATEGORY_TYPES, "Other / Consortium (Specify)")
                ed_cat_sel = st.selectbox("Category Type", MASTER_CATEGORY_TYPES, index=cat_idx, key=f"{sid}_sel_cat")
                ed_cat = ed_cat_sel
                if ed_cat_sel == "Other / Consortium (Specify)":
                    ed_cat_custom = st.text_input("Specify Category *", value=cat_custom, placeholder="e.g. Bilateral Consortium", key=f"{sid}_custom_cat")
                    if ed_cat_custom and ed_cat_custom.strip():
                        ed_cat = ed_cat_custom.strip()

                cur_stg = s.get("stage") or "Pre-Seed / Seed"
                stg_idx, stg_custom = resolve_field_choice(cur_stg, MASTER_STAGES, "Other / Multi-Stage (Specify)", default_index=1)
                ed_stage_sel = st.selectbox("Target Startup Stage", MASTER_STAGES, index=stg_idx, key=f"{sid}_sel_stg")
                ed_stage = ed_stage_sel
                if ed_stage_sel == "Other / Multi-Stage (Specify)":
                    ed_stg_custom = st.text_input("Specify Development Stage *", value=stg_custom, placeholder="e.g. Commercialization Phase", key=f"{sid}_custom_stg")
                    if ed_stg_custom and ed_stg_custom.strip():
                        ed_stage = ed_stg_custom.strip()

                cur_scope = s.get("state_scope") or s.get("geography") or "All India"
                scope_idx, scope_custom = resolve_field_choice(cur_scope, MASTER_GEOGRAPHIC_SCOPES, "Other / Specific Region (Specify)")
                ed_scope_sel = st.selectbox("Geographic Scope", MASTER_GEOGRAPHIC_SCOPES, index=scope_idx, key=f"{sid}_sel_scope")
                ed_scope = ed_scope_sel
                if ed_scope_sel == "Other / Specific Region (Specify)":
                    ed_scope_custom = st.text_input("Specify Geographic Region *", value=scope_custom, placeholder="e.g. South India / Tier 2 Cities", key=f"{sid}_custom_scope")
                    if ed_scope_custom and ed_scope_custom.strip():
                        ed_scope = ed_scope_custom.strip()

            c3, c4 = st.columns(2)
            with c3:
                ed_url = st.text_input("Official Application / Nodal Portal URL", value=s.get("application_url", ""))
            with c4:
                ed_verified = st.text_input("Last Verified Note", value=s.get("last_verified") or "August 2026")

        with tab2:
            raw_secs_val = s.get("sectors")
            raw_secs = []
            if isinstance(raw_secs_val, list):
                raw_secs = [str(x).strip() for x in raw_secs_val if str(x).strip()]
            elif isinstance(raw_secs_val, str):
                raw_s = raw_secs_val.strip()
                if raw_s.startswith("[") and raw_s.endswith("]"):
                    try:
                        parsed = json.loads(raw_s)
                        if isinstance(parsed, list):
                            raw_secs = [str(x).strip() for x in parsed if str(x).strip()]
                    except Exception:
                        pass
                if not raw_secs:
                    raw_secs = [x.strip() for x in raw_s.split(",") if x.strip()]

            standard_secs = []
            custom_secs = []
            for sec in raw_secs:
                m_match = next((ms for ms in MASTER_SECTORS if ms != "Other / Not Listed (Specify)" and ms.lower() == sec.lower()), None)
                if m_match:
                    if m_match not in standard_secs:
                        standard_secs.append(m_match)
                else:
                    if sec.strip():
                        custom_secs.append(sec.strip())

            default_sel = standard_secs.copy()
            if custom_secs:
                default_sel.append("Other / Not Listed (Specify)")
            if not default_sel:
                default_sel = ["Cross-Sector / All Sectors"]

            ed_sectors_sel = st.multiselect("Eligible Sectors *", MASTER_SECTORS, default=default_sel, key=f"{sid}_sel_sectors")
            ed_custom_sec = ""
            if "Other / Not Listed (Specify)" in ed_sectors_sel:
                default_custom_sec_str = ", ".join(custom_secs)
                ed_custom_sec = st.text_input("Specify Custom Sectors (comma-separated) *", value=default_custom_sec_str, placeholder="e.g. SpaceTech, Marine Biotechnology", key=f"{sid}_custom_sec")

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
                final_sectors = [x for x in ed_sectors_sel if x != "Other / Not Listed (Specify)"]
                if ed_custom_sec and ed_custom_sec.strip():
                    final_sectors.extend([x.strip() for x in ed_custom_sec.split(",") if x.strip()])
                if not final_sectors:
                    final_sectors = ["Cross-Sector / All Sectors"]

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
                    "sectors": final_sectors,
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
    st.markdown(f"<p style='color:#64748B; font-size:0.85rem;'>Scheme ID: <code>{_safe_esc(sid)}</code>.<br>This will permanently delete this funding opportunity from both local and cloud databases. This action cannot be undone.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Yes, Delete", type="primary", use_container_width=True):
            delete_scheme(sid, admin_id or "admin")
            st.success(f"Deleted '{name}'")
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

def render_fund_explorer_card(s: dict, is_admin: bool = False, admin_id: str = None, key_prefix: str = "fe", show_private_intelligence: bool = True, guide_recommendation: str = None):
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
        f'<span class="sector-tag" style="display:inline-block; font-size:0.7rem; font-weight:700; text-transform:uppercase; padding:3px 9px; border-radius:9999px; background:#1E293B !important; color:#E2E8F0 !important; border:1px solid #334155; margin-right:5px; margin-bottom:5px;">{_safe_esc(str(sec))}</span>'
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

    guide_rec_html = ""
    if guide_recommendation:
        guide_rec_html = f"""<div style="background:rgba(139,92,246,0.18);border-left:4px solid #8B5CF6;padding:0.75rem 0.9rem;border-radius:0 8px 8px 0;margin-bottom:0.75rem;">
<div style="font-size:0.76rem;font-weight:800;color:#C4B5FD;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px;">🎯 Guide Recommendation Note:</div>
<div style="font-size:0.86rem;color:#F1F5F9;line-height:1.45;">{_safe_esc(guide_recommendation)}</div>
</div>"""

    intelligence_html = ""
    if show_private_intelligence:
        intelligence_html = f"""<div class="intel-box" style="background:rgba(245,158,11,0.18) !important;border-left:4px solid #F59E0B;padding:0.75rem 0.9rem;border-radius:0 8px 8px 0;font-size:0.84rem;color:#FEF3C7 !important;line-height:1.45;margin-bottom:0.65rem;">
<div style="font-weight:800;color:#FBBF24 !important;margin-bottom:3px;font-size:0.84rem;letter-spacing:0.3px;">🤫 INSIDER INTELLIGENCE:</div>
<div style="color:#FEF3C7 !important;">{agenda_text}</div>
</div>
<div class="flag-box" style="background:rgba(239,68,68,0.18) !important;border-left:4px solid #EF4444;padding:0.75rem 0.9rem;border-radius:0 8px 8px 0;font-size:0.84rem;color:#FEE2E2 !important;line-height:1.45;margin-bottom:0.75rem;">
<div style="font-weight:800;color:#F87171 !important;margin-bottom:3px;font-size:0.84rem;letter-spacing:0.3px;">⚠️ RED FLAGS:</div>
<div style="color:#FEE2E2 !important;">{flag_text}</div>
</div>"""

    # Outer Container Card matching Playbook Fund Explorer
    st.markdown(f"""<div class="fund-explorer-card" style="background:#11131F !important;border:1.5px solid #8B5CF6;border-radius:14px;padding:1.25rem;margin-bottom:0.75rem;box-shadow:0 4px 20px rgba(139,92,246,0.12);">
{guide_rec_html}
<div style="margin-bottom:0.6rem;">
<div style="font-size:1.15rem;color:#FFFFFF;font-weight:800;line-height:1.3;margin:0 0 5px 0;">{_safe_esc(name, default='Untitled Scheme')}</div>
<div style="color:#94A3B8;font-size:0.84rem;margin:0;line-height:1.35;"><strong style="color:#CBD5E1;">Agency / Institution:</strong> {_safe_esc(agency, default='Government / Syndicate')}</div>
</div>
<div style="margin-bottom:0.75rem;display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
<span class="badge-fund" style="display:inline-block;font-size:0.68rem;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;padding:3px 10px;border-radius:9999px;background:rgba(139,92,246,0.22) !important;color:#C4B5FD !important;border:1px solid #8B5CF6;">{_safe_esc(fund_type, default='Grant')}</span>
<span class="badge-cat" style="display:inline-block;font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:9999px;background:rgba(59,130,246,0.15) !important;color:#93C5FD !important;border:1px solid #3B82F6;">{_safe_esc(cat_type, default='Central Govt')}</span>
{status_badge}
</div>
<div style="font-size:0.95rem;color:#34D399;font-weight:700;margin-bottom:0.65rem;line-height:1.35;">Funding: {_safe_esc(amount, default='Grant / Equity Support')}</div>
<div style="font-size:0.84rem;color:#CBD5E1;line-height:1.45;margin-bottom:0.85rem;">{_safe_esc(str(details or '')[:250])}</div>
<div style="margin-bottom:0.85rem;">{sectors_html}
<span class="badge-scope" style="display:inline-block;font-size:0.7rem;font-weight:700;text-transform:uppercase;padding:3px 9px;border-radius:9999px;background:rgba(16,185,129,0.15) !important;color:#34D399 !important;border:1px solid #059669;margin-bottom:5px;">{_safe_esc(scope_str, default='All India')}</span>
</div>
{intelligence_html}
<div style="display:flex;justify-content:space-between;align-items:center;padding-top:0.6rem;border-top:1px solid rgba(255,255,255,0.08);font-size:0.8rem;color:#94A3B8;margin-top:0.4rem;">
<div>{portal_link_html}</div>
<div>Verified: <strong style="color:#E2E8F0;">{_safe_esc(last_verified, default='Recent')}</strong></div>
</div>
</div>""", unsafe_allow_html=True)

    # Collapsible AI Pitch & Application Prompt Box (Guide/Admin only)
    if show_private_intelligence:
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
