# FULCRUM-INDIA: Cluster A

**Core Relationship + Profile + Journey + Communication + Scheme Intelligence System**

Rebuilt from first principles inside `Fulcrum-Alpha/fulcrum-cluster-a/` as a lightweight, secure, and maintainable **Streamlit + Supabase** application.

Cluster A replaces the legacy over-engineered enterprise architecture (FastAPI, Redis, Celery, Kafka, WebSockets, Docker) with a clean, low-cost architecture centered on the entrepreneur's chronological **Journey** ("The Movie / Post-Credits" model).

---

## 🏛️ Architectural Foundations

### Zero Enterprise Bloat
* **NO FastAPI** — Direct Streamlit service layer
* **NO Celery / Redis** — Synchronous and deterministic execution
* **NO Kafka** — Database-driven event logging
* **NO WebSockets** — Streamlit reactive state model
* **NO Docker / Kubernetes** — Zero container orchestration overhead

### Target Stack
* **Frontend UI**: Streamlit with custom CSS tokens (dark mode glassmorphism `#0B0F19`, Inter font, glowing status indicators, responsive cards, vertical timeline)
* **Identity & Authentication**: Supabase Auth (Email + Password, JWT sessions) + Database-driven roles
* **Database & Security**: PostgreSQL via Supabase Python client + Row Level Security (RLS) + resilient local SQLite fallback engine (`cluster_a.db`)
* **Data Core**: Hybrid schema — Relational core for foreign keys and relationships + JSONB for flexible profile data, journey event payloads, and scheme filters.

---

## 👥 The Four User Roles & Strict Invariants

| Role | Provisioning | Permissions & Boundaries |
| :--- | :--- | :--- |
| **Aspirant** | **Public Signup** | Can complete 4-part profile, view assigned Guide & SME, log own Journey entries, view deterministic scheme matches, and raise Help requests. |
| **Guide** | **Admin Only** (No public signup) | Dedicated mentor portal. Can view assigned Aspirants, inspect complete Journey, add mentorship entries (e.g. business model, pricing), and manage own contributions. |
| **SME** | **Admin Only** (No public signup) | Subject matter expert portal. Can view assigned Aspirants for specific domains (GST, legal, patents, food safety), inspect Journey, and contribute specialist guidance. |
| **Admin** | **Database-Driven** (`profiles.role='admin'`) | Command metrics, create Guide & SME accounts, exclusive assignment authority for mentors, global journey inspection, scheme catalogue CRUD, help queue resolution. |

> [!IMPORTANT]
> **Admin Authority Over Relationships**: Aspirants and Mentors (Guides/SMEs) cannot self-assign or assign each other. The Admin is the sole authority for assigning Guides and SMEs to Aspirants.

---

## 📁 Directory Structure

```
fulcrum-cluster-a/
├── app.py                     # Main Streamlit router & design token injector
├── requirements.txt           # Minimal, lean dependencies
├── README.md                  # System documentation
├── CLUSTER_A_TEST_MATRIX.md   # Comprehensive test matrix & verification plan
├── supabase_setup.sql         # Production PostgreSQL schema, functions & RLS policies
├── import_schemes.py          # Automated idempotent importer for 170 schemes
├── cluster_a.db               # Resilient local database store pre-seeded with 170 schemes
├── .streamlit/
│   ├── config.toml            # Server and theme configuration
│   └── secrets.toml           # Live Supabase connection keys
├── seed/
│   └── schemes.json           # Offline normalized backup of 170 schemes
├── pages/
│   ├── login.py               # FULCRUM-INDIA login & Aspirant public signup
│   ├── aspirant.py            # Aspirant portal (Overview, Profile, Journey, Mentors, Schemes, Help)
│   ├── guide.py               # Guide portal (Assigned aspirants & journey mentorship)
│   ├── sme.py                 # SME portal (Assigned cases & domain guidance)
│   └── admin.py               # Admin Control Tower (Metrics, Provisioning, Assignments, Help, Schemes)
└── services/
    ├── auth.py                # Supabase Auth, tokens & RBAC
    ├── profiles.py            # 4-part Naukri/LinkedIn profile engine & completion calculator
    ├── relationships.py       # Admin-driven Guide & SME assignment service
    ├── journey.py             # Chronological timeline & multi-actor event logger
    ├── schemes.py             # Scheme catalogue CRUD & deterministic matching engine
    ├── help_requests.py       # Support ticket lifecycle manager
    └── local_db.py            # Resilient SQLite local engine mirroring Supabase
```

---

## 🚀 Quickstart & Running Locally

### 1. Prerequisites
* Python 3.10+ (tested on Python 3.14)
* Virtual environment (optional but recommended)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 4. Default Seed Accounts for Testing

| Role | Email | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@fulcrum.in` | `Admin@123` | Full control tower access |
| **Aspirant** | `ravi.kumar@milletfoods.in` | `Aspirant@123` | Pre-configured demo Aspirant (Organic Millet Foods, Madurai) |
| **Guide** | `rajendran@fulcrum.in` | `Welcome@2026` | Pre-configured Guide (Enterprise Mentorship) |
| **SME** | `kumar.sme@fulcrum.in` | `Welcome@2026` | Pre-configured SME (GST & Tax Compliance) |

*You can also create a new Aspirant anytime via the **New Aspirant Sign Up** tab on the login screen.*

---

## 🏦 Scheme Intelligence Engine
* **Source**: Extracted directly from `FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html`.
* **Total Schemes**: Exactly **170 validated schemes** spanning central and state (Tamil Nadu) support.
* **Deterministic Matching**: Multi-factor scoring engine evaluating:
  1. State / Geography (e.g. Tamil Nadu state schemes)
  2. Sector / Industry (e.g. Food Processing, Agriculture, Manufacturing, IT)
  3. Enterprise Stage (Idea, Seed, Early-stage, Growth)
  4. Demographics (Women founders, SC/ST, OBC, Rural)
  5. Investment bracket
* **Explainability**: Every match shows an explicit breakdown of *"Why this matched"* (e.g., `✓ Located in Tamil Nadu`, `✓ Food Processing sector match`, `✓ Seed stage match`).
* **Terminology**: Strictly labeled **Recommended / Potentially Eligible** — never "Guaranteed" or "Approved".

---

## 🛡️ Database & Row Level Security (RLS)
The database script `supabase_setup.sql` configures:
* `public.profiles`: Relational core (`id`, `email`, `role`, `full_name`, `phone`, `district`, `state`) + `profile_data JSONB`.
* `public.relationships`: `aspirant_id`, `guide_id`, `sme_id`, `assigned_by`, `status`, `notes`.
* `public.journeys` & `public.journey_events`: Chronological append-only movie records with actor metadata (`actor_id`, `actor_role`) and soft deletion (`deleted_at`, `deleted_by`).
* `public.help_requests`: `aspirant_id`, `subject`, `message`, `priority`, `status`, `admin_response`.
* `public.schemes`: 170 scheme records with JSONB eligibility, sectors, hidden agenda, and terms.
* **RLS Policies**:
  * `profiles`: Users view their own; Admins view all; Guides/SMEs view assigned Aspirants.
  * `journey_events`: Aspirants view own; Guides/SMEs view assigned Aspirants; Creators edit/soft-delete own entries; Admins have full oversight.
  * `relationships`: Admin has write access; Aspirants and assigned Mentors have read access.
  * `schemes`: Public read access for active schemes; Admin write access for catalogue CRUD.
