"""
services/pdf_generator.py — Aspirant Dossier PDF Generator for FULCRUM-INDIA
=============================================================================
Generates a complete, audit-ready PDF dossier for any selected Aspirant.
Aggregates all data from Supabase (profile, mentors, schemes, journey, help
tickets) and renders an executive HTML document typeset in Montserrat,
then converts to PDF via Playwright Chrome Headless with ReportLab fallback.

This module is called exclusively from the Admin Dashboard download button.
Every query is scoped by aspirant_id — zero cross-contamination.
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

# ─────────────────────────────────────────────────────────────────────────
# DATA AGGREGATION
# ─────────────────────────────────────────────────────────────────────────

def _gather_aspirant_data(aspirant_id: str) -> Dict:
    """
    Aggregates ALL data for a single aspirant from the active data backend.
    Every query is scoped by aspirant_id — guaranteed isolation.
    Returns a dict with keys: profile, mentors, released_schemes,
    matched_schemes, journey_events, help_tickets.
    """
    from services.profiles import get_profile
    from services.relationships import get_aspirant_mentors
    from services.schemes import get_released_schemes_for_aspirant, match_schemes_for_aspirant
    from services.journey import get_journey_timeline
    from services.help_requests import list_requests, list_mentor_admin_queries

    profile = get_profile(aspirant_id) or {}
    mentors = get_aspirant_mentors(aspirant_id) or {}
    released_schemes = get_released_schemes_for_aspirant(aspirant_id) or []
    matched_schemes = match_schemes_for_aspirant(aspirant_id, limit=15, min_score=50) or []
    journey_events = get_journey_timeline(aspirant_id) or []
    help_tickets = list_requests(aspirant_id=aspirant_id) or []
    mentor_admin_queries = list_mentor_admin_queries(aspirant_id=aspirant_id) or []

    return {
        "profile": profile,
        "mentors": mentors,
        "released_schemes": released_schemes,
        "matched_schemes": matched_schemes,
        "journey_events": journey_events,
        "help_tickets": help_tickets,
        "mentor_admin_queries": mentor_admin_queries,
    }


# ─────────────────────────────────────────────────────────────────────────
# HTML RENDERING
# ─────────────────────────────────────────────────────────────────────────

def _safe(val, default="—"):
    """HTML-escape a value, returning a default if empty."""
    import html as html_mod
    if val is None or str(val).strip() == "":
        return default
    return html_mod.escape(str(val).strip())


def _badge_html(text: str, bg: str = "#E0E7FF", color: str = "#3730A3") -> str:
    return f'<span style="display:inline-block;padding:3px 10px;border-radius:4px;font-weight:700;font-size:11px;background:{bg};color:{color};margin:2px 3px 2px 0;">{_safe(text)}</span>'


def _section_header(title: str, icon: str = "") -> str:
    return f'''
    <div style="margin-top:28px;margin-bottom:10px;border-bottom:2px solid #1E293B;padding-bottom:6px;">
        <h2 style="font-size:16px;font-weight:800;color:#1E293B;margin:0;letter-spacing:0.5px;">{icon} {title}</h2>
    </div>'''


def _kv_row(label: str, value: str) -> str:
    return f'''
    <tr>
        <td style="padding:5px 12px 5px 0;font-weight:600;color:#475569;font-size:12px;white-space:nowrap;vertical-align:top;">{label}</td>
        <td style="padding:5px 0;color:#0F172A;font-size:12px;">{value}</td>
    </tr>'''


def _render_dossier_html(data: Dict) -> str:
    """Builds the complete executive HTML dossier from aggregated data."""
    profile = data["profile"]
    mentors = data["mentors"]
    released_schemes = data["released_schemes"]
    matched_schemes = data["matched_schemes"]
    journey_events = data["journey_events"]
    help_tickets = data["help_tickets"]

    p_data = profile.get("profile_data") or {}
    if isinstance(p_data, str):
        try:
            p_data = json.loads(p_data)
        except Exception:
            p_data = {}

    personal = p_data.get("personal", {})
    professional = p_data.get("professional", {})
    business = p_data.get("business", {})
    demographics = p_data.get("demographics", {})

    full_name = _safe(profile.get("full_name"), "Aspirant")
    email = _safe(profile.get("email"))
    phone = _safe(profile.get("phone"))
    district = _safe(profile.get("district"))
    state = _safe(profile.get("state"), "Tamil Nadu")

    # Document metadata
    doc_ref = f"FULCRUM-DOSSIER-{str(uuid.uuid4())[:8].upper()}"
    gen_time = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    guide = mentors.get("guide")
    sme = mentors.get("sme")

    # ── Start HTML ──
    html_parts = [f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FULCRUM Dossier — {full_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
@page {{
    size: A4;
    margin: 15mm 18mm;
}}
@media print {{
    .page-break {{ page-break-before: always; }}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
    color: #0F172A;
    font-size: 12px;
    line-height: 1.55;
    background: #fff;
}}
h1 {{ font-size: 22px; font-weight: 800; color: #0F172A; }}
h2 {{ font-size: 16px; font-weight: 800; color: #1E293B; }}
h3 {{ font-size: 13px; font-weight: 700; color: #334155; }}
table {{ border-collapse: collapse; width: 100%; }}
.header-bar {{
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
    color: #fff;
    padding: 22px 28px;
    border-radius: 0;
    margin-bottom: 0;
}}
.header-bar h1 {{ color: #fff; font-size: 20px; letter-spacing: 1px; }}
.header-bar .sub {{ color: #94A3B8; font-size: 11px; margin-top: 4px; }}
.meta-strip {{
    background: #F1F5F9;
    padding: 8px 28px;
    font-size: 10px;
    color: #64748B;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #E2E8F0;
    margin-bottom: 18px;
}}
.card {{
    background: #FAFBFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
}}
.card-title {{
    font-size: 13px;
    font-weight: 700;
    color: #1E293B;
    margin-bottom: 8px;
}}
.scheme-row {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
.timeline-item {{
    border-left: 3px solid #CBD5E1;
    padding: 8px 0 8px 16px;
    margin-bottom: 6px;
    position: relative;
}}
.timeline-item::before {{
    content: '';
    position: absolute;
    left: -6px;
    top: 12px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #3B82F6;
    border: 2px solid #fff;
}}
.ticket-card {{
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
.footer {{
    margin-top: 30px;
    padding-top: 12px;
    border-top: 2px solid #1E293B;
    font-size: 9px;
    color: #94A3B8;
    text-align: center;
}}
</style>
</head>
<body>

<!-- ═══════ EXECUTIVE HEADER ═══════ -->
<div class="header-bar">
    <h1>FULCRUM-INDIA — Enterprise Guidance System</h1>
    <div class="sub">CONFIDENTIAL — Founder Dossier & Journey Report</div>
</div>
<div class="meta-strip">
    <span>Document Ref: {doc_ref}</span>
    <span>Generated: {gen_time}</span>
    <span>Classification: INTERNAL — ADMIN USE ONLY</span>
</div>
''']

    # ═══════ SECTION 1: FOUNDER & DEMOGRAPHIC PROFILE ═══════
    html_parts.append(_section_header("FOUNDER & DEMOGRAPHIC PROFILE", "👤"))

    # Statutory badges
    badge_items = []
    cat = demographics.get("category") or demographics.get("founder_category") or demographics.get("social_category", "")
    if cat:
        badge_items.append(_badge_html(cat, "#FEF3C7", "#92400E"))
    gender = personal.get("gender") or demographics.get("gender", "")
    if gender and str(gender).lower() in ("female", "woman"):
        badge_items.append(_badge_html("Women-Led Venture", "#FCE7F3", "#9D174D"))
    if demographics.get("differently_abled") or str(demographics.get("differently_abled", "")).lower() in ("yes", "true"):
        badge_items.append(_badge_html("Differently-Abled", "#DBEAFE", "#1E40AF"))
    if demographics.get("minority") or str(demographics.get("minority", "")).lower() in ("yes", "true"):
        badge_items.append(_badge_html("Minority", "#E0E7FF", "#3730A3"))
    if demographics.get("ex_serviceman") or str(demographics.get("ex_serviceman", "")).lower() in ("yes", "true"):
        badge_items.append(_badge_html("Ex-Serviceman", "#D1FAE5", "#065F46"))
    dpiit = business.get("dpiit_registered") or demographics.get("dpiit_registered", "")
    if str(dpiit).lower() in ("yes", "true"):
        badge_items.append(_badge_html("DPIIT Registered", "#CCFBF1", "#115E59"))
    startup_tn = business.get("startup_tn_registered") or demographics.get("startup_tn_registered", "")
    if str(startup_tn).lower() in ("yes", "true"):
        badge_items.append(_badge_html("StartupTN Registered", "#CCFBF1", "#115E59"))

    badges_html = " ".join(badge_items) if badge_items else _badge_html("No Quota Declared", "#F1F5F9", "#94A3B8")

    html_parts.append(f'''
    <div class="card">
        <table>
            {_kv_row("Full Name", f"<strong>{full_name}</strong>")}
            {_kv_row("Email", email)}
            {_kv_row("Phone", phone)}
            {_kv_row("District", district)}
            {_kv_row("State", state)}
            {_kv_row("Gender", _safe(gender))}
            {_kv_row("Date of Birth", _safe(personal.get("dob")))}
            {_kv_row("Address", _safe(personal.get("address")))}
        </table>
        <div style="margin-top:10px;">
            <span style="font-weight:700;font-size:11px;color:#475569;">Statutory Quotas & Registrations:</span><br>
            {badges_html}
        </div>
    </div>''')

    # Education & Professional
    html_parts.append(f'''
    <div class="card">
        <div class="card-title">Education & Professional Background</div>
        <table>
            {_kv_row("Education", _safe(professional.get("education")))}
            {_kv_row("Skills", _safe(professional.get("skills")))}
            {_kv_row("Experience", _safe(professional.get("experience") or professional.get("experience_years")))}
            {_kv_row("Expertise / Domain", _safe(professional.get("expertise")))}
            {_kv_row("Certifications", _safe(professional.get("certifications")))}
        </table>
    </div>''')

    # ═══════ SECTION 2: ENTERPRISE & VENTURE ═══════
    html_parts.append(_section_header("ENTERPRISE & VENTURE ARCHITECTURE", "🏢"))
    html_parts.append(f'''
    <div class="card">
        <table>
            {_kv_row("Enterprise Name", f"<strong>{_safe(business.get('business_name'))}</strong>")}
            {_kv_row("Legal Entity Type", _safe(business.get("business_type") or business.get("legal_status")))}
            {_kv_row("Industry Sector", _safe(business.get("sector")))}
            {_kv_row("Sub-Sector", _safe(business.get("sub_sector")))}
            {_kv_row("Development Stage", _safe(business.get("stage")))}
            {_kv_row("Operational District", _safe(business.get("location") or district))}
            {_kv_row("Employee Headcount", _safe(business.get("team_size") or business.get("employees")))}
            {_kv_row("Annual Revenue Bracket", _safe(business.get("revenue")))}
            {_kv_row("Year Founded", _safe(business.get("founded") or business.get("founded_year")))}
            {_kv_row("DPIIT Registration", _safe(dpiit))}
            {_kv_row("StartupTN Registration", _safe(startup_tn))}
        </table>
        <div style="margin-top:8px;">
            <span style="font-weight:700;font-size:11px;color:#475569;">Venture Summary:</span>
            <p style="font-size:12px;color:#334155;margin-top:4px;">{_safe(business.get("description") or business.get("brief"), "No venture description provided.")}</p>
        </div>
    </div>''')

    # ═══════ SECTION 3: ASSIGNED GUIDANCE NETWORK ═══════
    html_parts.append(_section_header("ASSIGNED GUIDANCE NETWORK", "🤝"))
    guide_html = "<em>Not yet assigned</em>"
    if guide:
        guide_html = f'''<table>
            {_kv_row("Full Name", f"<strong>{_safe(guide.get('full_name'))}</strong>")}
            {_kv_row("Email", _safe(guide.get("email")))}
            {_kv_row("Phone", _safe(guide.get("phone")))}
            {_kv_row("Organization", _safe((guide.get("profile_data") or {}).get("professional", {}).get("expertise", "")))}
        </table>'''

    sme_html = "<em>Not yet assigned</em>"
    if sme:
        sme_html = f'''<table>
            {_kv_row("Full Name", f"<strong>{_safe(sme.get('full_name'))}</strong>")}
            {_kv_row("Email", _safe(sme.get("email")))}
            {_kv_row("Phone", _safe(sme.get("phone")))}
            {_kv_row("Specialization", _safe((sme.get("profile_data") or {}).get("professional", {}).get("expertise", "")))}
        </table>'''

    html_parts.append(f'''
    <div style="display:flex;gap:14px;">
        <div class="card" style="flex:1;">
            <div class="card-title">Primary Guide</div>
            {guide_html}
        </div>
        <div class="card" style="flex:1;">
            <div class="card-title">SME Specialist</div>
            {sme_html}
        </div>
    </div>''')

    # ═══════ SECTION 4: GOVERNMENT SCHEMES & CAPITAL ═══════
    html_parts.append('<div class="page-break"></div>')
    html_parts.append(_section_header("GOVERNMENT SCHEMES & CAPITAL ALLOCATION", "🏦"))

    # Released / Allocated schemes
    if released_schemes:
        html_parts.append('<h3 style="margin:10px 0 6px 0;font-size:13px;color:#059669;">Allocated / Released Schemes</h3>')
        for s in released_schemes:
            s_name = _safe(s.get("name") or s.get("scheme_name"))
            s_id = _safe(s.get("id") or s.get("scheme_id"))
            ministry = _safe(s.get("ministry") or s.get("department"))
            grant_val = _safe(s.get("max_funding") or s.get("funding_amount") or s.get("financial_support"))
            rec = _safe(s.get("guide_recommendation"), "No recommendation note")
            note = _safe(s.get("guide_note"), "")
            released_at = str(s.get("released_at", ""))[:19]
            html_parts.append(f'''
            <div class="scheme-row">
                <div style="font-weight:700;font-size:13px;color:#0F172A;">{s_name}</div>
                <div style="font-size:11px;color:#64748B;margin:2px 0;">ID: {s_id} · Ministry: {ministry} · Grant: {grant_val}</div>
                <div style="font-size:11px;color:#059669;margin-top:4px;"><strong>Guide Recommendation:</strong> {rec}</div>
                {"<div style='font-size:11px;color:#475569;'><strong>Note:</strong> " + note + "</div>" if note != "—" else ""}
                <div style="font-size:10px;color:#94A3B8;margin-top:3px;">Released: {released_at}</div>
            </div>''')
    else:
        html_parts.append('<div class="card"><em>No schemes have been released to this Aspirant yet.</em></div>')

    # Top matched schemes
    if matched_schemes:
        html_parts.append('<h3 style="margin:14px 0 6px 0;font-size:13px;color:#2563EB;">Top Algorithmic Matches</h3>')
        for m in matched_schemes[:10]:
            s_name = _safe(m.get("name") or m.get("scheme_name"))
            score = m.get("match_score", 0)
            reason = _safe(m.get("match_reason") or m.get("reason", ""))
            ministry = _safe(m.get("ministry") or m.get("department"))
            grant_val = _safe(m.get("max_funding") or m.get("funding_amount") or m.get("financial_support"))

            score_color = "#059669" if score >= 75 else "#D97706" if score >= 60 else "#6B7280"
            html_parts.append(f'''
            <div class="scheme-row" style="border-left:3px solid {score_color};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;font-size:12px;color:#0F172A;">{s_name}</div>
                    <span style="font-weight:800;font-size:14px;color:{score_color};">{score}%</span>
                </div>
                <div style="font-size:11px;color:#64748B;">Ministry: {ministry} · Grant: {grant_val}</div>
                <div style="font-size:11px;color:#475569;margin-top:3px;">{reason}</div>
            </div>''')

    # ═══════ SECTION 5: CHRONOLOGICAL JOURNEY TIMELINE ═══════
    html_parts.append(_section_header("COMPLETE CHRONOLOGICAL JOURNEY", "📜"))

    if journey_events:
        actor_colors = {
            "aspirant": ("#EFF6FF", "#1D4ED8", "ASPIRANT"),
            "guide": ("#F0FDF4", "#059669", "GUIDE"),
            "sme": ("#FEF3C7", "#D97706", "DOMAIN SME"),
            "admin": ("#FEF2F2", "#DC2626", "ADMIN"),
            "system": ("#F1F5F9", "#475569", "SYSTEM AUTOMATION"),
        }
        for ev in journey_events:
            role = str(ev.get("actor_role", "system")).lower()
            bg_c, txt_c, label = actor_colors.get(role, ("#F1F5F9", "#475569", role.upper()))
            ev_date = str(ev.get("event_date", ""))[:19]
            actor_name = _safe(ev.get("actor_name", "System"))
            if role == "system":
                actor_name = "Platform Intelligence"
            elif not actor_name:
                actor_name = "Contributor"
            title = _safe(ev.get("title", ev.get("event_type", "Event")))
            desc = _safe(ev.get("description", ""))

            html_parts.append(f'''
            <div class="timeline-item" style="border-left-color:{txt_c};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        {_badge_html(label, bg_c, txt_c)}
                        <span style="font-weight:700;font-size:12px;color:#0F172A;">{title}</span>
                    </div>
                    <span style="font-size:10px;color:#94A3B8;">{ev_date}</span>
                </div>
                <div style="font-size:11px;color:#475569;margin-top:3px;">Contributor: <strong>{actor_name}</strong> ({label})</div>
                <div style="font-size:11px;color:#334155;margin-top:4px;">{desc}</div>
            </div>''')
    else:
        html_parts.append('<div class="card"><em>No journey events recorded yet.</em></div>')

    # ═══════ SECTION 6: SUPPORT & HELP TICKETS ═══════
    html_parts.append('<div class="page-break"></div>')
    html_parts.append(_section_header("SUPPORT & COMMUNICATION TICKETS", "💬"))

    if help_tickets:
        status_colors = {
            "OPEN": ("#FEF3C7", "#92400E"),
            "IN_PROGRESS": ("#DBEAFE", "#1E40AF"),
            "RESOLVED": ("#D1FAE5", "#065F46"),
            "ESCALATED": ("#FEE2E2", "#991B1B"),
        }
        for t in help_tickets:
            t_status = t.get("status", "OPEN")
            s_bg, s_clr = status_colors.get(t_status, ("#F1F5F9", "#64748B"))
            subject = _safe(t.get("subject"))
            message = _safe(t.get("message"))
            priority = _safe(t.get("priority", "MEDIUM"))
            created = str(t.get("created_at", ""))[:19]
            guide_resp = t.get("guide_response", "")
            sme_resp = t.get("sme_response", "")
            admin_resp = t.get("admin_response", "")

            html_parts.append(f'''
            <div class="ticket-card" style="background:{s_bg};border-color:{s_clr}40;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;font-size:12px;color:{s_clr};">{subject}</div>
                    {_badge_html(t_status, s_bg, s_clr)}
                </div>
                <div style="font-size:11px;color:#475569;margin-top:4px;">Priority: {priority} · Submitted: {created}</div>
                <div style="font-size:11px;color:#334155;margin-top:4px;"><strong>Message:</strong> {_safe(message)}</div>''')

            if guide_resp:
                html_parts.append(f'''
                <div style="background:#F0FDF4;border-left:3px solid #10B981;padding:6px 10px;margin-top:6px;border-radius:0 4px 4px 0;font-size:11px;color:#166534;">
                    <strong>Guide Response:</strong> {_safe(guide_resp)}
                </div>''')
            if sme_resp:
                html_parts.append(f'''
                <div style="background:#FFFBEB;border-left:3px solid #F59E0B;padding:6px 10px;margin-top:6px;border-radius:0 4px 4px 0;font-size:11px;color:#92400E;">
                    <strong>SME Specialist Advisory:</strong> {_safe(sme_resp)}
                </div>''')
            if admin_resp:
                html_parts.append(f'''
                <div style="background:#EFF6FF;border-left:3px solid #3B82F6;padding:6px 10px;margin-top:4px;border-radius:0 4px 4px 0;font-size:11px;color:#1E40AF;">
                    <strong>Admin Resolution:</strong> {_safe(admin_resp)}
                </div>''')

            html_parts.append('</div>')
    else:
        html_parts.append('<div class="card"><em>No support tickets raised by this Aspirant.</em></div>')

    # ═══════ SECTION 7: ADMINISTRATIVE AUDIT TRAIL (CONFIDENTIAL) ═══════
    mentor_queries = data.get("mentor_admin_queries") or []
    html_parts.append('<div class="page-break"></div>')
    html_parts.append(_section_header("CONFIDENTIAL ADMINISTRATIVE GOVERNANCE & DIRECTIVES", "🏛️"))
    html_parts.append('''
    <div style="font-size:11px;color:#64748B;margin-bottom:10px;font-style:italic;">
        Privileged Directorate Records: Institutional roadblocks escalated by Guides/SMEs to Administration and official Directorate Directives. Invisible to the Aspirant.
    </div>''')

    if mentor_queries:
        for mq in mentor_queries:
            mq_status = mq.get("status", "PENDING_ADMIN")
            s_bg, s_clr = ("#ECFDF5", "#065F46") if mq_status == "DIRECTIVE_ISSUED" else ("#FEF3C7", "#92400E")
            subject = _safe(mq.get("subject"))
            message = _safe(mq.get("message"))
            priority = _safe(mq.get("priority", "MEDIUM"))
            created = str(mq.get("created_at", ""))[:19]
            req_role = _safe(str(mq.get("requester_role", "Mentor")).upper())
            directive = mq.get("admin_directive") or mq.get("admin_response", "")
            directive_at = str(mq.get("directive_issued_at", ""))[:19]

            html_parts.append(f'''
            <div class="ticket-card" style="background:#F8FAFC;border-left:4px solid #475569;margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;font-size:12px;color:#0F172A;">{subject}</div>
                    {_badge_html(mq_status, s_bg, s_clr)}
                </div>
                <div style="font-size:11px;color:#64748B;margin-top:3px;">
                    Initiator: <strong>{req_role}</strong> · Priority: {priority} · Logged: {created}
                </div>
                <div style="font-size:11px;color:#334155;margin-top:6px;">
                    <strong>Institutional Roadblock Context:</strong> {_safe(message)}
                </div>''')

            if directive:
                html_parts.append(f'''
                <div style="background:#F0FDF4;border-left:3px solid #16A34A;padding:8px 12px;margin-top:8px;border-radius:0 6px 6px 0;font-size:11px;color:#14532D;">
                    <div style="font-weight:800;letter-spacing:0.5px;color:#15803D;margin-bottom:2px;">OFFICIAL DIRECTORATE DIRECTIVE:</div>
                    <div>{_safe(directive)}</div>
                    <div style="font-size:10px;color:#166534;margin-top:4px;">Issued: {directive_at}</div>
                </div>''')
            else:
                html_parts.append('''
                <div style="background:#FEF2F2;border-left:3px solid #EF4444;padding:6px 10px;margin-top:6px;border-radius:0 4px 4px 0;font-size:11px;color:#991B1B;">
                    <strong>Status:</strong> Pending Administrative Directorate Review & Action
                </div>''')

            html_parts.append('</div>')
    else:
        html_parts.append('<div class="card"><em>No institutional mentor roadblocks or administrative directives recorded for this mentee.</em></div>')

    # ═══════ INSTITUTIONAL FOOTER ═══════
    html_parts.append(f'''
    <div class="footer">
        <div style="font-weight:700;color:#475569;font-size:10px;margin-bottom:4px;">FULCRUM-INDIA ENTERPRISE GUIDANCE SYSTEM</div>
        <div>Document Ref: {doc_ref} · Generated: {gen_time}</div>
        <div style="margin-top:4px;">This document is confidential and intended solely for authorized administrative use within the FULCRUM-INDIA platform.</div>
        <div style="margin-top:2px;">Unauthorized reproduction, distribution, or disclosure is strictly prohibited.</div>
    </div>

</body>
</html>''')

    return "\n".join(html_parts)


# ─────────────────────────────────────────────────────────────────────────
# PDF CONVERSION — DUAL ENGINE (Playwright Primary, ReportLab Fallback)
# ─────────────────────────────────────────────────────────────────────────

def _convert_html_to_pdf_playwright(html_content: str) -> Optional[bytes]:
    """
    Primary engine: Writes HTML to a temp file and runs Playwright in an
    ISOLATED SUBPROCESS to avoid Streamlit's threading/event-loop conflicts.
    Returns pixel-perfect A4 PDF bytes with Google Fonts Montserrat.
    """
    html_path = None
    pdf_path = None
    try:
        # Write HTML to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_path = f.name

        # Create temp path for output PDF
        pdf_path = html_path.replace('.html', '.pdf')

        worker_script = os.path.join(os.path.dirname(__file__), "html_to_pdf_worker.py")
        result = subprocess.run(
            [sys.executable, worker_script, html_path, pdf_path],
            capture_output=True,
            text=True,
            timeout=45
        )

        if result.returncode == 0 and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pf:
                pdf_bytes = pf.read()
            if len(pdf_bytes) > 1000:
                return pdf_bytes

        err_msg = result.stderr.strip() if result.stderr else 'unknown error'
        print(f"[PDFGenerator] Subprocess Playwright worker error (exit {result.returncode}): {err_msg[:500]}")
        return None

    except Exception as e:
        print(f"[PDFGenerator] Playwright subprocess engine failed: {e}")
        return None
    finally:
        for path in [html_path, pdf_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass


def _convert_html_to_pdf_reportlab(html_content: str, full_name: str = "Aspirant") -> Optional[bytes]:
    """
    Fallback engine: Uses ReportLab to generate a structured PDF.
    Properly strips CSS/style blocks before text extraction.
    """
    try:
        import io
        import re
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18*mm,
            rightMargin=18*mm,
            topMargin=18*mm,
            bottomMargin=20*mm
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="DossierTitle",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=HexColor("#0F172A"),
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name="DossierBody",
            fontName="Helvetica",
            fontSize=10,
            textColor=HexColor("#334155"),
            leading=14,
            spaceAfter=6
        ))
        styles.add(ParagraphStyle(
            name="DossierSection",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=HexColor("#1E293B"),
            spaceBefore=18,
            spaceAfter=8,
        ))

        story = []
        story.append(Paragraph("FULCRUM-INDIA -- Enterprise Guidance System", styles["DossierTitle"]))
        story.append(Paragraph(f"Founder Dossier: {full_name}", styles["DossierSection"]))
        story.append(Spacer(1, 8))

        # Strip style/script blocks FIRST, then HTML tags
        clean = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<head[^>]*>.*?</head>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', '\n', clean)
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n\s*\n', '\n', clean).strip()

        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        for line in lines[:200]:
            # Escape special ReportLab characters
            safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_line, styles["DossierBody"]))

        doc.build(story)
        return buffer.getvalue()
    except Exception as e:
        print(f"[PDFGenerator] ReportLab fallback also failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────

def generate_aspirant_dossier_pdf(aspirant_id: str) -> bytes:
    """
    Main entry point. Called from Admin Dashboard download button.
    Aggregates data for a single aspirant, renders HTML dossier in
    Montserrat, converts to PDF via subprocess-isolated Playwright.

    Returns: PDF bytes (ready for st.download_button data=).
    """
    import sys

    data = _gather_aspirant_data(aspirant_id)
    full_name = data["profile"].get("full_name", "Aspirant")
    html_content = _render_dossier_html(data)

    # Primary: Playwright Chrome Headless in isolated subprocess
    pdf_bytes = _convert_html_to_pdf_playwright(html_content)
    if pdf_bytes and len(pdf_bytes) > 1000:
        print(f"[PDFGenerator] OK Playwright PDF generated for '{full_name}': {len(pdf_bytes)} bytes")
        return pdf_bytes

    # Fallback: ReportLab
    print(f"[PDFGenerator] WARN Falling back to ReportLab for '{full_name}'")
    pdf_bytes = _convert_html_to_pdf_reportlab(html_content, full_name)
    if pdf_bytes and len(pdf_bytes) > 100:
        print(f"[PDFGenerator] OK ReportLab PDF generated for '{full_name}': {len(pdf_bytes)} bytes")
        return pdf_bytes

    # Last resort: Return error PDF placeholder
    print(f"[PDFGenerator] FAIL Both engines failed for '{full_name}'")
    return b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"

