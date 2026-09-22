"""
services/constants.py — Central Taxonomy & Master Constants for FULCRUM-INDIA
=============================================================================
Unified vocabulary shared across:
- Aspirant Profile UI (views/aspirant.py)
- Public Signup Form (views/login.py)
- Admin Scheme Creator & Editor (views/admin.py, services/schemes_ui.py)
- Deterministic Matching Engine (services/schemes.py)
- Guide & SME workspaces (views/guide.py, views/sme.py)

Every dropdown provides an intuitive, professional fallback option:
- 'Other / Not Listed (Specify)'
- 'Other District / Non-TN (Specify)'
- 'Other / Hybrid (Specify)'
- 'All Stages / Stage-Agnostic' or 'Other / Multi-Stage (Specify)'
This guarantees founders, mentors, and admins are never locked out of custom niches.
"""

import html
from typing import Tuple, List, Optional

def safe_escape(val, default="") -> str:
    """Crash-proof HTML escape that safely handles None, booleans, and non-string types."""
    if val is None:
        return html.escape(str(default))
    return html.escape(str(val))

_safe_esc = safe_escape

# ── 1. INDUSTRY SECTORS ──
MASTER_SECTORS = [
    "Food Processing & Agribusiness",
    "Agriculture & Allied",
    "Manufacturing & Engineering",
    "Technology & SaaS",
    "DeepTech, AI & Hardware",
    "Healthcare & MedTech",
    "GreenTech, Clean Energy & EV",
    "Textiles, Apparel & Handloom",
    "Fintech & Financial Services",
    "Consumer Goods, Retail & D2C",
    "Biotech & Life Sciences",
    "Logistics, Supply Chain & Mobility",
    "Education & EdTech",
    "Tourism, Hospitality & Services",
    "Cross-Sector / All Sectors",
    "Other / Not Listed (Specify)"
]

# ── 2. VENTURE DEVELOPMENT STAGES ──
MASTER_STAGES = [
    "Ideation / R&D",
    "Pre-Seed / Seed",
    "Pre-Series A / Series A",
    "Growth / Debt Scaling",
    "All Stages / Stage-Agnostic",
    "Other / Multi-Stage (Specify)"
]

STAGE_DESCRIPTIONS = {
    "Ideation / R&D": "Concept stage, R&D validation, or lab prototype (Pre-revenue).",
    "Pre-Seed / Seed": "Working MVP or early customer traction with annual revenue under Rs.50 Lakh.",
    "Pre-Series A / Series A": "Proven product-market fit, scaling customer acquisition, institutional growth.",
    "Growth / Debt Scaling": "Established, profitable, or mature enterprise seeking expansion capital.",
    "All Stages / Stage-Agnostic": "Scheme or grant is accessible to ventures at any stage of development.",
    "Other / Multi-Stage (Specify)": "Venture stage spans multiple maturity phases or unique structuring."
}

# ── 3. TAMIL NADU DISTRICTS (All 38 Revenue Districts + Out-of-State) ──
MASTER_DISTRICTS_TN = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kanchipuram",
    "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
    "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
    "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur",
    "Vellore", "Viluppuram", "Virudhunagar",
    "Other District / Non-TN (Specify)"
]

# ── 4. BUSINESS & ENTERPRISE STRUCTURES ──
MASTER_BUSINESS_TYPES = [
    "Manufacturing",
    "Services",
    "Trading / Retail Distribution",
    "Tech / Digital Product",
    "Agri & Processing",
    "Other / Hybrid (Specify)"
]

# ── 5. SOCIAL & AFFIRMATIVE CATEGORIES ──
MASTER_SOCIAL_CATEGORIES = [
    "General",
    "OBC",
    "MBC / DNC",
    "SC",
    "ST",
    "Minority",
    "Other / Prefer Not to Disclose"
]

# ── 6. GENDER IDENTITY ──
MASTER_GENDERS = [
    "Male",
    "Female",
    "Transgender / Non-Binary",
    "Other / Prefer Not to Say"
]

# ── 7. FUNDING & CAPITAL TYPES ──
MASTER_FUNDING_TYPES = [
    "Grant",
    "Subsidy + Support",
    "Capital Subsidy",
    "Equity / Angel Investment",
    "Soft Loan / Low-Interest Debt",
    "Credit Guarantee (CGTMSE)",
    "Compute / GPU Subsidy",
    "Reimbursement Grant",
    "Convertible Note / SAFE",
    "Other / Blended Capital (Specify)"
]

# ── 8. SCHEME / FUND JURISDICTION CATEGORIES ──
MASTER_CATEGORY_TYPES = [
    "Central Govt",
    "State Govt",
    "Private VC / Angel",
    "Foreign / Global",
    "Corporate CSR / Foundation",
    "Other / Consortium (Specify)"
]

# ── 9. GEOGRAPHIC SCOPE ──
MASTER_GEOGRAPHIC_SCOPES = [
    "Tamil Nadu",
    "All India",
    "Regional / Specific States",
    "Global / International",
    "Other / Specific Region (Specify)"
]


# ─────────────────────────────────────────────────────────────────────────────
# TAXONOMY RESOLUTION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def resolve_field_choice(
    current_value: Optional[str],
    master_list: List[str],
    other_label: str,
    default_index: int = 0
) -> Tuple[int, str]:
    """
    Intelligently maps a stored string to a dropdown index and an optional custom string.
    
    Returns:
        (dropdown_index, custom_text_value)
    
    If current_value exactly matches an option in master_list (other than other_label),
    returns (index, "").
    If current_value is custom or matches other_label, returns (other_label_index, current_value).
    If current_value is empty, returns (default_index, "").
    """
    if not current_value:
        return default_index, ""
    
    val_clean = str(current_value).strip()
    
    # 1. Exact match with a standard master option
    for idx, opt in enumerate(master_list):
        if opt != other_label and opt.lower() == val_clean.lower():
            return idx, ""
            
    # 2. Fuzzy / substring match with a standard master option
    for idx, opt in enumerate(master_list):
        if opt != other_label and (val_clean.lower() in opt.lower() or opt.lower() in val_clean.lower()):
            return idx, ""
            
    # 3. Custom value -> select the 'Other' option and prefill the custom text
    if other_label in master_list:
        other_idx = master_list.index(other_label)
        custom_fill = "" if val_clean.lower() == other_label.lower() else val_clean
        return other_idx, custom_fill
        
    return default_index, ""
