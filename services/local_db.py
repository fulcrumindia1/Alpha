"""
services/local_db.py — Resilient Persistent Local Database Engine
==================================================================
Implements identical PostgreSQL schema and relationships in SQLite
to ensure 100% testability, zero crashes, and seamless synchronization
with Supabase cloud tables.
"""

import sqlite3
import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "cluster_a.db"

class LocalDatabase:
    def __init__(self, db_file: Path = DB_PATH):
        self.db_file = db_file
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()

        # 1. Profiles
        cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('aspirant', 'guide', 'sme', 'admin')),
            full_name TEXT NOT NULL,
            phone TEXT,
            district TEXT,
            state TEXT DEFAULT 'Tamil Nadu',
            profile_data TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            password_hash TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 2. Relationships
        cur.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            aspirant_id TEXT UNIQUE NOT NULL REFERENCES profiles(id),
            guide_id TEXT REFERENCES profiles(id),
            sme_id TEXT REFERENCES profiles(id),
            sme_ids TEXT DEFAULT '[]',
            assigned_by TEXT REFERENCES profiles(id),
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 3. Journeys
        cur.execute("""
        CREATE TABLE IF NOT EXISTS journeys (
            id TEXT PRIMARY KEY,
            aspirant_id TEXT UNIQUE NOT NULL REFERENCES profiles(id),
            title TEXT NOT NULL,
            business_type TEXT,
            stage TEXT DEFAULT 'idea',
            start_date TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 4. Journey Events
        cur.execute("""
        CREATE TABLE IF NOT EXISTS journey_events (
            id TEXT PRIMARY KEY,
            journey_id TEXT NOT NULL REFERENCES journeys(id),
            aspirant_id TEXT NOT NULL REFERENCES profiles(id),
            actor_id TEXT NOT NULL REFERENCES profiles(id),
            actor_role TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT NOT NULL DEFAULT '{}',
            event_date TEXT,
            deleted_at TEXT,
            deleted_by TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 5. Help Requests
        cur.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id TEXT PRIMARY KEY,
            aspirant_id TEXT NOT NULL REFERENCES profiles(id),
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'MEDIUM',
            status TEXT DEFAULT 'OPEN',
            admin_response TEXT,
            responded_by TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 6. Schemes
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            name TEXT NOT NULL,
            agency TEXT,
            ministry TEXT,
            scheme_type TEXT,
            category_type TEXT,
            funding_type TEXT,
            stage TEXT,
            amount TEXT,
            brief TEXT,
            description TEXT,
            sectors TEXT DEFAULT '[]',
            eligibility TEXT DEFAULT '[]',
            terms TEXT DEFAULT '[]',
            hidden_agenda TEXT DEFAULT '[]',
            red_flags TEXT DEFAULT '[]',
            process TEXT,
            timeline TEXT,
            success_rate TEXT,
            contact TEXT,
            state_scope TEXT,
            geography TEXT,
            application_url TEXT,
            last_verified TEXT,
            application_prompt TEXT,
            source_dataset TEXT,
            status TEXT DEFAULT 'active',
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 9999,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 7. Activity Log
        cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT,
            details TEXT DEFAULT '{}',
            created_at TEXT
        );
        """)

        # 8. Scheme Releases (Guide Governance & Visibility Gate)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS scheme_releases (
            id TEXT PRIMARY KEY,
            aspirant_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            guide_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            scheme_id TEXT NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'RELEASED' CHECK(status IN ('DRAFT', 'RELEASED', 'WITHDRAWN')),
            guide_note TEXT,
            guide_recommendation TEXT,
            eligibility_summary TEXT,
            released_at TEXT,
            released_by TEXT REFERENCES profiles(id),
            withdrawn_at TEXT,
            withdrawn_by TEXT REFERENCES profiles(id),
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(aspirant_id, scheme_id)
        );
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_aspirant ON scheme_releases(aspirant_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_guide ON scheme_releases(guide_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_scheme ON scheme_releases(scheme_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_status ON scheme_releases(status);")

        # 9. Notifications (In-App Universal Alert System)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            actor_id TEXT REFERENCES profiles(id),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, created_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notif_unread ON notifications(user_id, is_read);")

        # 10. Assignment History (Roster Transition & Audit Log)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignment_history (
            id TEXT PRIMARY KEY,
            aspirant_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            mentor_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            mentor_role TEXT NOT NULL CHECK(mentor_role IN ('guide', 'sme')),
            assigned_by TEXT REFERENCES profiles(id),
            action TEXT NOT NULL CHECK(action IN ('ASSIGNED', 'REPLACED', 'UNASSIGNED')),
            previous_mentor_id TEXT REFERENCES profiles(id),
            notes TEXT,
            created_at TEXT
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asghist_asp ON assignment_history(aspirant_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asghist_mentor ON assignment_history(mentor_id);")

        conn.commit()

        # Dynamic schema migration: ensure display_order exists in schemes table
        cur.execute("PRAGMA table_info(schemes)")
        existing_cols = [r[1] for r in cur.fetchall()]
        if "display_order" not in existing_cols:
            try:
                cur.execute("ALTER TABLE schemes ADD COLUMN display_order INTEGER DEFAULT 9999")
                conn.commit()
            except Exception as e:
                print(f"[LocalDB] Migration notice: {e}")

        # Dynamic schema migration: ensure sme_ids and guide_ids exist in relationships table
        cur.execute("PRAGMA table_info(relationships)")
        rel_cols = [r[1] for r in cur.fetchall()]
        if "sme_ids" not in rel_cols:
            try:
                cur.execute("ALTER TABLE relationships ADD COLUMN sme_ids TEXT DEFAULT '[]'")
                conn.commit()
            except Exception as e:
                print(f"[LocalDB] Relationships migration notice (sme_ids): {e}")
        if "guide_ids" not in rel_cols:
            try:
                cur.execute("ALTER TABLE relationships ADD COLUMN guide_ids TEXT DEFAULT '[]'")
                conn.commit()
            except Exception as e:
                print(f"[LocalDB] Relationships migration notice (guide_ids): {e}")

        # Dynamic schema migration: ensure guide routing & escalation columns exist in help_requests
        cur.execute("PRAGMA table_info(help_requests)")
        hr_cols = [r[1] for r in cur.fetchall()]
        if "assigned_guide_id" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN assigned_guide_id TEXT REFERENCES profiles(id)")
            except Exception: pass
        if "assigned_at" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN assigned_at TEXT")
            except Exception: pass
        if "last_handled_at" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN last_handled_at TEXT")
            except Exception: pass
        if "escalated_at" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN escalated_at TEXT")
            except Exception: pass
        if "escalation_reason" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN escalation_reason TEXT")
            except Exception: pass
        if "resolved_by" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN resolved_by TEXT REFERENCES profiles(id)")
            except Exception: pass
        if "guide_response" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN guide_response TEXT")
            except Exception: pass
        if "category" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN category TEXT DEFAULT 'GENERAL'")
            except Exception: pass
        if "assigned_sme_id" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN assigned_sme_id TEXT REFERENCES profiles(id)")
            except Exception: pass
        if "sme_response" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN sme_response TEXT")
            except Exception: pass
        if "target_role" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN target_role TEXT DEFAULT 'guide'")
            except Exception: pass
        if "requester_id" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN requester_id TEXT REFERENCES profiles(id)")
            except Exception: pass
        if "requester_role" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN requester_role TEXT DEFAULT 'aspirant'")
            except Exception: pass
        if "request_type" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN request_type TEXT DEFAULT 'aspirant_consultation'")
            except Exception: pass
        if "category_detail" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN category_detail TEXT")
            except Exception: pass
        if "admin_directive" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN admin_directive TEXT")
            except Exception: pass
        if "directive_issued_at" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN directive_issued_at TEXT")
            except Exception: pass
        if "aspirant_response" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN aspirant_response TEXT")
            except Exception: pass
        if "aspirant_responded_at" not in hr_cols:
            try: cur.execute("ALTER TABLE help_requests ADD COLUMN aspirant_responded_at TEXT")
            except Exception: pass
        conn.commit()

        # Seed default demo accounts (Admin, Guide, SME, Aspirant) if missing
        cur.execute("SELECT id FROM profiles WHERE role = 'admin' LIMIT 1")
        if not cur.fetchone():
            now_iso = datetime.now(timezone.utc).isoformat()
            # 1. Admin
            admin_id = "72655c43-9f13-4309-a8a0-194570a6c2aa"
            admin_pw_hash = hashlib.sha256("Admin@123".encode("utf-8")).hexdigest()
            cur.execute("""
            INSERT INTO profiles (id, email, role, full_name, phone, district, state, password_hash, profile_data, is_active, created_at, updated_at)
            VALUES (?, ?, 'admin', 'Fulcrum Administrator', '9876543213', 'Chennai', 'Tamil Nadu', ?, '{}', 1, ?, ?)
            """, (admin_id, "admin@fulcrum.in", admin_pw_hash, now_iso, now_iso))

            # 2. Guide
            guide_id = "a21158e5-7850-4cad-94d2-1ef69e177765"
            guide_pw_hash = hashlib.sha256("Welcome@2026".encode("utf-8")).hexdigest()
            guide_data = json.dumps({"expertise": "Enterprise Strategy, Agribusiness Scaling", "bio": "Senior Enterprise Guide with 15+ years experience mentoring MSMEs.", "industry": "Agribusiness", "temp_password_issued": True})
            cur.execute("""
            INSERT INTO profiles (id, email, role, full_name, phone, district, state, password_hash, profile_data, is_active, created_at, updated_at)
            VALUES (?, ?, 'guide', 'Rajendran Natarajan', '9840123456', 'Chennai', 'Tamil Nadu', ?, ?, 1, ?, ?)
            """, (guide_id, "rajendran@fulcrum.in", guide_pw_hash, guide_data, now_iso, now_iso))

            # 3. SME
            sme_id = "953bdd1a-5aeb-4919-84a7-8ac0c3b0b47f"
            sme_pw_hash = hashlib.sha256("Welcome@2026".encode("utf-8")).hexdigest()
            sme_data = json.dumps({"expertise": "GST, Indirect Taxation & FSSAI Compliance", "bio": "Specialized Chartered Accountant & Compliance Consultant.", "industry": "Taxation & Regulatory", "temp_password_issued": True})
            cur.execute("""
            INSERT INTO profiles (id, email, role, full_name, phone, district, state, password_hash, profile_data, is_active, created_at, updated_at)
            VALUES (?, ?, 'sme', 'Kumar S.', '9840654321', 'Madurai', 'Tamil Nadu', ?, ?, 1, ?, ?)
            """, (sme_id, "kumar.sme@fulcrum.in", sme_pw_hash, sme_data, now_iso, now_iso))

            # 4. Aspirant (Ravi Kumar)
            asp_id = "6e667c86-84d3-4b65-b727-90f71f2b2875"
            asp_pw_hash = hashlib.sha256("Aspirant@123".encode("utf-8")).hexdigest()
            asp_data = json.dumps({
                "personal": {"full_name": "Ravi Kumar", "email": "ravi.kumar@milletfoods.in", "phone": "9876543210", "district": "Madurai", "state": "Tamil Nadu", "gender": "Male", "dob": "15-08-1995", "address": "12 Main Road, Madurai"},
                "professional": {"education": "B.Sc Agriculture", "experience_years": 4, "skills": ["Food Processing", "Supply Chain", "Retail"], "current_status": "Full-time Founder", "experience": "3 years in food manufacturing", "certifications": "FSSAI Basic, MSME EDI Training"},
                "business": {"business_name": "Organic Millet Foods", "business_type": "Manufacturing", "sector": "Food Processing", "stage": "Pre-Seed / Seed", "investment_bracket": "10L-25L", "revenue": "₹12,00,000 / year", "employee_count": 3, "description": "Nutritional value-added millet products for urban families."},
                "demographics": {"district": "Madurai", "state": "Tamil Nadu", "founder_category": "OBC", "social_category": "OBC", "gender": "Male", "is_dpiit_recognized": True, "is_startuptn_registered": True, "is_women_led": False}
            })
            cur.execute("""
            INSERT INTO profiles (id, email, role, full_name, phone, district, state, password_hash, profile_data, is_active, created_at, updated_at)
            VALUES (?, ?, 'aspirant', 'Ravi Kumar', '9876543210', 'Madurai', 'Tamil Nadu', ?, ?, 1, ?, ?)
            """, (asp_id, "ravi.kumar@milletfoods.in", asp_pw_hash, asp_data, now_iso, now_iso))

            # 5. Journey Record
            journey_id = "j-6e667c86-84d3-4b65-b727-90f71f2b2875"
            cur.execute("""
            INSERT OR REPLACE INTO journeys (id, aspirant_id, title, status, created_at, updated_at)
            VALUES (?, ?, 'Venture Formation & Scale Journey', 'active', ?, ?)
            """, (journey_id, asp_id, now_iso, now_iso))

            # 6. Default Relationship
            rel_id = "05ce7f60-99b6-4228-b9cb-0e0b8338f546"
            cur.execute("""
            INSERT OR REPLACE INTO relationships (id, aspirant_id, guide_id, sme_id, assigned_by, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', 'Dedicated Enterprise Mentor and Compliance SME assigned.', ?, ?)
            """, (rel_id, asp_id, guide_id, sme_id, admin_id, now_iso, now_iso))

            # 7. Milestone events
            cur.execute("""
            INSERT OR REPLACE INTO journey_events (id, journey_id, aspirant_id, actor_id, actor_role, event_type, event_data, event_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'aspirant', 'BUSINESS_STARTED', ?, '2026-01-10', ?, ?)
            """, ("ev-seed-1", journey_id, asp_id, asp_id, json.dumps({"title": "Started Business", "description": "Founded Organic Millet Foods in Madurai to produce value-added millet health mixes.", "category": "Inception"}), now_iso, now_iso))

            cur.execute("""
            INSERT OR REPLACE INTO journey_events (id, journey_id, aspirant_id, actor_id, actor_role, event_type, event_data, event_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'guide', 'MENTOR_SESSION', ?, '2026-02-01', ?, ?)
            """, ("ev-seed-2", journey_id, asp_id, guide_id, json.dumps({"title": "Refined Pricing & GTM Strategy", "description": "Helped Ravi refine retail pack pricing and identify B2B retail distribution channels.", "category": "Mentorship"}), now_iso, now_iso))

            cur.execute("""
            INSERT OR REPLACE INTO journey_events (id, journey_id, aspirant_id, actor_id, actor_role, event_type, event_data, event_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'sme', 'DOMAIN_ADVISORY', ?, '2026-02-15', ?, ?)
            """, ("ev-seed-3", journey_id, asp_id, sme_id, json.dumps({"title": "GST & FSSAI Compliance Roadmap", "description": "Advised on GST threshold exemptions and completed mandatory FSSAI food licensing filing.", "category": "Compliance"}), now_iso, now_iso))

            conn.commit()

        # Seed 170 schemes from seed/schemes.json if empty
        cur.execute("SELECT COUNT(*) FROM schemes")
        count = cur.fetchone()[0]
        if count == 0:
            seed_json = Path(__file__).resolve().parent.parent / "seed" / "schemes.json"
            if seed_json.exists():
                try:
                    with open(seed_json, "r", encoding="utf-8") as f:
                        schemes_list = json.load(f)
                    for idx, s in enumerate(schemes_list):
                        cur.execute("""
                        INSERT OR REPLACE INTO schemes (
                            id, source_id, name, agency, ministry, scheme_type, category_type,
                            funding_type, stage, amount, brief, description, sectors, eligibility,
                            terms, hidden_agenda, red_flags, process, timeline, success_rate,
                            contact, state_scope, geography, application_url, last_verified,
                            application_prompt, source_dataset, status, is_active, display_order, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            s["id"], s.get("source_id"), s["name"], s.get("agency"), s.get("ministry"),
                            s.get("scheme_type"), s.get("category_type"), s.get("funding_type"), s.get("stage"),
                            s.get("amount"), s.get("brief"), s.get("description"),
                            json.dumps(s.get("sectors", [])), json.dumps(s.get("eligibility", [])),
                            json.dumps(s.get("terms", [])), json.dumps(s.get("hidden_agenda", [])),
                            json.dumps(s.get("red_flags", [])), s.get("process"), s.get("timeline"),
                            s.get("success_rate"), s.get("contact"), s.get("state_scope"), s.get("geography"),
                            s.get("application_url"), s.get("last_verified"), s.get("application_prompt"),
                            s.get("source_dataset"), s.get("status", "active"), 1 if s.get("is_active", True) else 0,
                            s.get("display_order", idx + 1),
                            datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()
                        ))
                    conn.commit()
                except Exception as e:
                    print(f"[LocalDB] Notice seeding schemes: {e}")

        conn.close()

    # ── PASSWORD HELPERS ──
    @staticmethod
    def hash_pw(pw: str) -> str:
        return hashlib.sha256(pw.encode("utf-8")).hexdigest()

    def verify_password(self, email: str, password: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM profiles WHERE LOWER(email) = ?", (email.lower(),))
        row = cur.fetchone()
        conn.close()
        if not row or not row["password_hash"]:
            return False
        return row["password_hash"] == self.hash_pw(password)

    def create_user_with_password(self, email: str, password: str, profile: Dict) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        pw_hash = self.hash_pw(password)
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_email = email.lower().strip()

        cur.execute("SELECT id FROM profiles WHERE email = ?", (clean_email,))
        existing = cur.fetchone()
        user_id = existing["id"] if existing else profile["id"]
        profile["id"] = user_id

        cur.execute("""
        INSERT INTO profiles (id, email, role, full_name, phone, district, state, profile_data, is_active, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            email = excluded.email,
            full_name = excluded.full_name,
            role = excluded.role,
            phone = excluded.phone,
            district = excluded.district,
            state = excluded.state,
            profile_data = excluded.profile_data,
            password_hash = excluded.password_hash,
            updated_at = excluded.updated_at
        """, (
            user_id, clean_email, profile.get("role", "aspirant"),
            profile.get("full_name", ""), profile.get("phone", ""),
            profile.get("district", "Madurai"), profile.get("state", "Tamil Nadu"),
            json.dumps(profile.get("profile_data", {})),
            1 if profile.get("is_active", True) else 0,
            pw_hash, now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return profile

    def update_user_password(self, user_id: str, new_password: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        pw_hash = self.hash_pw(new_password)
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE profiles SET password_hash = ?, updated_at = ? WHERE id = ?", (pw_hash, now_iso, user_id))
        count = cur.rowcount
        conn.commit()
        conn.close()
        return count > 0

    # ── PROFILES ──
    def get_profile_by_id(self, user_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        d["profile_data"] = json.loads(d["profile_data"]) if d.get("profile_data") else {}
        d.pop("password_hash", None)
        return d

    def get_profile_by_email(self, email: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE LOWER(email) = ?", (email.lower(),))
        row = cur.fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        d["profile_data"] = json.loads(d["profile_data"]) if d.get("profile_data") else {}
        d.pop("password_hash", None)
        return d

    def upsert_profile(self, profile: Dict) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO profiles (id, email, role, full_name, phone, district, state, profile_data, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            full_name = excluded.full_name,
            phone = excluded.phone,
            district = excluded.district,
            state = excluded.state,
            profile_data = excluded.profile_data,
            updated_at = excluded.updated_at
        """, (
            profile["id"], profile["email"].lower(), profile.get("role", "aspirant"),
            profile.get("full_name", ""), profile.get("phone", ""),
            profile.get("district", "Madurai"), profile.get("state", "Tamil Nadu"),
            json.dumps(profile.get("profile_data", {})),
            1 if profile.get("is_active", True) else 0,
            now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return profile

    def list_profiles_by_role(self, role: str) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE role = ? AND is_active = 1 ORDER BY created_at DESC", (role,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["profile_data"] = json.loads(d["profile_data"]) if d.get("profile_data") else {}
            d.pop("password_hash", None)
            res.append(d)
        return res

    # ── RELATIONSHIPS ──
    def get_relationship(self, aspirant_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM relationships WHERE aspirant_id = ?", (aspirant_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        if d.get("sme_ids"):
            try:
                d["sme_ids"] = json.loads(d["sme_ids"])
            except Exception:
                d["sme_ids"] = []
        else:
            d["sme_ids"] = []
        return d

    def assign_guide(self, aspirant_id: str, guide_id: str, admin_id: str, notes: str = ""):
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        import uuid
        cur.execute("""
        INSERT INTO relationships (id, aspirant_id, guide_id, assigned_by, notes, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(aspirant_id) DO UPDATE SET
            guide_id = excluded.guide_id,
            assigned_by = excluded.assigned_by,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """, (str(uuid.uuid4()), aspirant_id, guide_id, admin_id, notes, now_iso, now_iso))
        conn.commit()
        conn.close()

    def assign_sme(self, aspirant_id: str, sme_id: str, admin_id: str, notes: str = "", mode: str = "add"):
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        import uuid

        cur.execute("SELECT id, sme_id, sme_ids FROM relationships WHERE aspirant_id = ?", (aspirant_id,))
        row = cur.fetchone()

        sme_ids_list = []
        if row:
            existing_sme_id = row["sme_id"]
            raw_sme_ids = row["sme_ids"] if "sme_ids" in row.keys() else None
            if raw_sme_ids:
                try:
                    sme_ids_list = json.loads(raw_sme_ids)
                except Exception:
                    sme_ids_list = []
            if existing_sme_id and existing_sme_id not in sme_ids_list:
                sme_ids_list.insert(0, existing_sme_id)

        if mode == "add":
            if sme_id not in sme_ids_list:
                sme_ids_list.append(sme_id)
        else:
            sme_ids_list = [sme_id]

        new_sme_ids_json = json.dumps(sme_ids_list)

        cur.execute("""
        INSERT INTO relationships (id, aspirant_id, sme_id, sme_ids, assigned_by, notes, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(aspirant_id) DO UPDATE SET
            sme_id = excluded.sme_id,
            sme_ids = excluded.sme_ids,
            assigned_by = excluded.assigned_by,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """, (str(uuid.uuid4()), aspirant_id, sme_id, new_sme_ids_json, admin_id, notes, now_iso, now_iso))
        conn.commit()
        conn.close()

    def list_aspirants_for_guide(self, guide_id: str) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        SELECT p.*, r.notes as assignment_notes
        FROM profiles p
        JOIN relationships r ON p.id = r.aspirant_id
        WHERE (r.guide_id = ? OR r.guide_ids LIKE ?) AND p.is_active = 1
        ORDER BY r.created_at DESC
        """, (guide_id, f'%"{guide_id}"%'))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["profile_data"] = json.loads(d["profile_data"]) if d.get("profile_data") else {}
            d.pop("password_hash", None)
            res.append(d)
        return res

    def list_aspirants_for_sme(self, sme_id: str) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        SELECT p.*, r.notes as assignment_notes
        FROM profiles p
        JOIN relationships r ON p.id = r.aspirant_id
        WHERE (r.sme_id = ? OR r.sme_ids LIKE ?) AND p.is_active = 1
        ORDER BY r.created_at DESC
        """, (sme_id, f'%"{sme_id}"%'))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["profile_data"] = json.loads(d["profile_data"]) if d.get("profile_data") else {}
            d.pop("password_hash", None)
            res.append(d)
        return res

    # ── JOURNEYS ──
    def create_initial_journey(self, aspirant_id: str, title: str):
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        import uuid
        cur.execute("""
        INSERT INTO journeys (id, aspirant_id, title, business_type, stage, start_date, status, created_at, updated_at)
        VALUES (?, ?, ?, 'Entrepreneurship', 'idea', date('now'), 'active', ?, ?)
        ON CONFLICT(aspirant_id) DO NOTHING
        """, (str(uuid.uuid4()), aspirant_id, title, now_iso, now_iso))
        conn.commit()
        conn.close()

    def get_journey(self, aspirant_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM journeys WHERE aspirant_id = ?", (aspirant_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_journey_event(self, journey_id: str, aspirant_id: str, actor_id: str, actor_role: str, event_type: str, event_data: Dict, event_date: Optional[str] = None) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        event_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        if not event_date:
            event_date = now_iso

        cur.execute("""
        INSERT INTO journey_events (id, journey_id, aspirant_id, actor_id, actor_role, event_type, event_data, event_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, journey_id, aspirant_id, actor_id, actor_role, event_type,
            json.dumps(event_data), event_date, now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "id": event_id,
            "journey_id": journey_id,
            "aspirant_id": aspirant_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "event_type": event_type,
            "event_data": event_data,
            "title": event_data.get("title", event_type),
            "description": event_data.get("description", ""),
            "event_date": event_date
        }

    def get_journey_events(self, aspirant_id: str) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        SELECT e.*, p.full_name as actor_name
        FROM journey_events e
        LEFT JOIN profiles p ON e.actor_id = p.id
        WHERE e.aspirant_id = ? AND e.deleted_at IS NULL
        ORDER BY e.event_date DESC, e.created_at DESC
        """, (aspirant_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["event_data"] = json.loads(d["event_data"]) if d.get("event_data") else {}
            d["title"] = d["event_data"].get("title", d.get("event_type", "Event"))
            d["description"] = d["event_data"].get("description", "")
            d["included_in_roadmap"] = d["event_data"].get("included_in_roadmap", True)
            res.append(d)
        return res

    def toggle_journey_event_inclusion(
        self,
        event_id: str,
        aspirant_id: str,
        included: bool,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Toggles whether an event is included in the aspirant's journey roadmap, verifying ownership and role authorization."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT event_data, aspirant_id FROM journey_events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False, "Journey event not found."

        raw_data = row[0]
        ev_aspirant_id = row[1]

        # 1. Verify that event belongs to the requested aspirant
        if not ev_aspirant_id or str(ev_aspirant_id) != str(aspirant_id):
            conn.close()
            return False, "Unauthorized: Event does not belong to the specified aspirant."

        # 2. If actor_id is provided, verify it matches the owning aspirant
        if actor_id and str(actor_id) != str(ev_aspirant_id):
            conn.close()
            return False, "Unauthorized: You can only alter roadmap inclusion for your own journey."

        # 3. If actor_role is provided, verify it is 'aspirant'
        if actor_role and actor_role != "aspirant":
            conn.close()
            return False, f"Permission denied: {actor_role.capitalize()}s cannot alter the entrepreneur's personal roadmap inclusion."

        try:
            ev_data = json.loads(raw_data) if raw_data else {}
        except Exception:
            ev_data = {}
        ev_data["included_in_roadmap"] = bool(included)
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE journey_events
        SET event_data = ?, updated_at = ?
        WHERE id = ? AND aspirant_id = ?
        """, (json.dumps(ev_data), now_iso, event_id, aspirant_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        if changes > 0:
            return True, None
        return False, "Database update produced no changes."

    def soft_delete_journey_event(self, event_id: str, deleted_by: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE journey_events
        SET deleted_at = ?, deleted_by = ?
        WHERE id = ?
        """, (now_iso, deleted_by, event_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    # ── HELP REQUESTS ──
    def create_help_request(
        self,
        aspirant_id: str,
        subject: str,
        message: str,
        priority: str = "MEDIUM",
        assigned_guide_id: Optional[str] = None,
        category: str = "GENERAL",
        assigned_sme_id: Optional[str] = None,
        target_role: str = "guide",
        category_detail: Optional[str] = None
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        req_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        assigned_at = now_iso if (assigned_guide_id or assigned_sme_id) else None
        cur.execute("""
        INSERT INTO help_requests (
            id, aspirant_id, subject, message, priority, status,
            assigned_guide_id, assigned_sme_id, category, target_role,
            category_detail, assigned_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id, aspirant_id, subject, message, priority,
            assigned_guide_id, assigned_sme_id, category, target_role,
            category_detail, assigned_at, now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "status": "OPEN",
            "assigned_guide_id": assigned_guide_id,
            "assigned_sme_id": assigned_sme_id,
            "category": category,
            "category_detail": category_detail,
            "target_role": target_role,
            "assigned_at": assigned_at,
            "created_at": now_iso
        }

    def list_help_requests(
        self,
        aspirant_id: Optional[str] = None,
        guide_id: Optional[str] = None,
        sme_id: Optional[str] = None
    ) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        if aspirant_id:
            cur.execute("""
            SELECT h.*, p.full_name as aspirant_name, p.email as aspirant_email,
                   g.full_name as guide_name, s.full_name as sme_name
            FROM help_requests h
            JOIN profiles p ON h.aspirant_id = p.id
            LEFT JOIN profiles g ON h.assigned_guide_id = g.id
            LEFT JOIN profiles s ON h.assigned_sme_id = s.id
            WHERE h.aspirant_id = ? AND (h.request_type IS NULL OR h.request_type != 'mentor_admin_query')
            ORDER BY h.created_at DESC
            """, (aspirant_id,))
        elif guide_id:
            cur.execute("""
            SELECT h.*, p.full_name as aspirant_name, p.email as aspirant_email,
                   g.full_name as guide_name, s.full_name as sme_name
            FROM help_requests h
            JOIN profiles p ON h.aspirant_id = p.id
            LEFT JOIN profiles g ON h.assigned_guide_id = g.id
            LEFT JOIN profiles s ON h.assigned_sme_id = s.id
            WHERE (h.assigned_guide_id = ?
               OR (h.assigned_guide_id IS NULL AND h.aspirant_id IN (SELECT aspirant_id FROM relationships WHERE guide_id = ?)))
               AND (h.target_role IS NULL OR h.target_role != 'sme')
               AND (h.request_type IS NULL OR h.request_type != 'mentor_admin_query')
            ORDER BY h.created_at DESC
            """, (guide_id, guide_id))
        elif sme_id:
            cur.execute("""
            SELECT h.*, p.full_name as aspirant_name, p.email as aspirant_email,
                   g.full_name as guide_name, s.full_name as sme_name
            FROM help_requests h
            JOIN profiles p ON h.aspirant_id = p.id
            LEFT JOIN profiles g ON h.assigned_guide_id = g.id
            LEFT JOIN profiles s ON h.assigned_sme_id = s.id
            WHERE (h.assigned_sme_id = ?
               OR (h.assigned_sme_id IS NULL AND h.aspirant_id IN (SELECT aspirant_id FROM relationships WHERE sme_id = ?)))
               AND (h.target_role == 'sme' OR h.assigned_sme_id = ?)
               AND (h.request_type IS NULL OR h.request_type != 'mentor_admin_query')
            ORDER BY h.created_at DESC
            """, (sme_id, sme_id, sme_id))
        else:
            cur.execute("""
            SELECT h.*, p.full_name as aspirant_name, p.email as aspirant_email,
                   g.full_name as guide_name, s.full_name as sme_name
            FROM help_requests h
            JOIN profiles p ON h.aspirant_id = p.id
            LEFT JOIN profiles g ON h.assigned_guide_id = g.id
            LEFT JOIN profiles s ON h.assigned_sme_id = s.id
            WHERE (h.request_type IS NULL OR h.request_type != 'mentor_admin_query')
            ORDER BY h.created_at DESC
            """)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_help_request_status(self, request_id: str, status: str, admin_response: str, responded_by: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        resolved_by = responded_by if status == "RESOLVED" else None
        cur.execute("""
        UPDATE help_requests
        SET status = ?, admin_response = ?, responded_by = ?, resolved_by = COALESCE(resolved_by, ?), updated_at = ?
        WHERE id = ?
        """, (status, admin_response, responded_by, resolved_by, now_iso, request_id))
        conn.commit()
        conn.close()
        return True

    def guide_respond_help_request(self, request_id: str, guide_id: str, status: str, guide_response: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        resolved_by = guide_id if status == "RESOLVED" else None
        cur.execute("""
        UPDATE help_requests
        SET status = ?, guide_response = ?, last_handled_at = ?, resolved_by = COALESCE(resolved_by, ?), updated_at = ?
        WHERE id = ? AND (assigned_guide_id = ? OR assigned_guide_id IS NULL)
        """, (status, guide_response, now_iso, resolved_by, now_iso, request_id, guide_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def sme_respond_help_request(self, request_id: str, sme_id: str, status: str, sme_response: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        resolved_by = sme_id if status == "RESOLVED" else None
        cur.execute("""
        UPDATE help_requests
        SET status = ?, sme_response = ?, last_handled_at = ?, resolved_by = COALESCE(resolved_by, ?), updated_at = ?
        WHERE id = ? AND (assigned_sme_id = ? OR assigned_sme_id IS NULL)
        """, (status, sme_response, now_iso, resolved_by, now_iso, request_id, sme_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def create_mentor_consultation(
        self,
        mentor_id: str,
        mentor_role: str,
        aspirant_id: str,
        subject: str,
        message: str,
        priority: str = "MEDIUM",
        category: str = "GENERAL",
        category_detail: Optional[str] = None
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        req_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        assigned_guide_id = mentor_id if mentor_role == "guide" else None
        assigned_sme_id = mentor_id if mentor_role == "sme" else None
        target_role = mentor_role
        cur.execute("""
        INSERT INTO help_requests (
            id, aspirant_id, subject, message, priority, status,
            assigned_guide_id, assigned_sme_id, category, target_role,
            requester_id, requester_role, request_type, category_detail,
            assigned_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, 'mentor_initiated', ?, ?, ?, ?)
        """, (
            req_id, aspirant_id, subject, message, priority,
            assigned_guide_id, assigned_sme_id, category, target_role,
            mentor_id, mentor_role, category_detail,
            now_iso, now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "status": "OPEN",
            "assigned_guide_id": assigned_guide_id,
            "assigned_sme_id": assigned_sme_id,
            "category": category,
            "target_role": target_role,
            "requester_id": mentor_id,
            "requester_role": mentor_role,
            "request_type": "mentor_initiated",
            "category_detail": category_detail,
            "created_at": now_iso
        }

    def aspirant_respond_help_request(self, request_id: str, aspirant_id: str, response: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE help_requests
        SET status = 'IN_PROGRESS', aspirant_response = ?, aspirant_responded_at = ?, last_handled_at = ?, updated_at = ?
        WHERE id = ? AND aspirant_id = ?
        """, (response, now_iso, now_iso, now_iso, request_id, aspirant_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def create_mentor_admin_query(
        self,
        mentor_id: str,
        mentor_role: str,
        aspirant_id: str,
        subject: str,
        message: str,
        priority: str = "MEDIUM"
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        req_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO help_requests (
            id, aspirant_id, subject, message, priority, status,
            requester_id, requester_role, request_type,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'PENDING_ADMIN', ?, ?, 'mentor_admin_query', ?, ?)
        """, (
            req_id, aspirant_id, subject, message, priority,
            mentor_id, mentor_role, now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "id": req_id,
            "aspirant_id": aspirant_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "status": "PENDING_ADMIN",
            "requester_id": mentor_id,
            "requester_role": mentor_role,
            "request_type": "mentor_admin_query",
            "created_at": now_iso
        }

    def list_mentor_admin_queries(
        self,
        mentor_id: Optional[str] = None,
        aspirant_id: Optional[str] = None
    ) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        params = []
        where_clauses = ["h.request_type = 'mentor_admin_query'"]
        if mentor_id:
            where_clauses.append("h.requester_id = ?")
            params.append(mentor_id)
        if aspirant_id:
            where_clauses.append("h.aspirant_id = ?")
            params.append(aspirant_id)
        where_str = " AND ".join(where_clauses)
        cur.execute(f"""
        SELECT h.*, p.full_name as aspirant_name, p.email as aspirant_email,
               m.full_name as requester_name, m.role as requester_role_actual
        FROM help_requests h
        LEFT JOIN profiles p ON h.aspirant_id = p.id
        LEFT JOIN profiles m ON h.requester_id = m.id
        WHERE {where_str}
        ORDER BY h.created_at DESC
        """, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def admin_respond_to_mentor_query(
        self,
        query_id: str,
        admin_id: str,
        directive: str,
        new_status: str = "DIRECTIVE_ISSUED"
    ) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE help_requests
        SET status = ?, admin_directive = ?, directive_issued_at = ?, responded_by = ?, updated_at = ?
        WHERE id = ?
        """, (new_status, directive, now_iso, admin_id, now_iso, query_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    # ── NOTIFICATIONS (In-App Alert System) ──
    def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str,
        actor_id: Optional[str] = None,
        link: Optional[str] = None
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        notif_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO notifications (id, user_id, actor_id, title, message, notification_type, link, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (notif_id, user_id, actor_id, title, message, notification_type, link, now_iso))
        conn.commit()
        conn.close()
        return {
            "id": notif_id,
            "user_id": user_id,
            "actor_id": actor_id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "link": link,
            "is_read": False,
            "created_at": now_iso
        }

    def list_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        if unread_only:
            cur.execute("""
            SELECT * FROM notifications
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
            """, (user_id,))
        else:
            cur.execute("""
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """, (user_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE id = ? AND user_id = ?
        """, (notification_id, user_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def mark_all_notifications_as_read(self, user_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def get_unread_notifications_count(self, user_id: str) -> int:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_id = ? AND is_read = 0
        """, (user_id,))
        count = cur.fetchone()[0]
        conn.close()
        return int(count)

    # ── ASSIGNMENT HISTORY ──
    def record_assignment_history(
        self,
        aspirant_id: str,
        mentor_id: str,
        mentor_role: str,
        assigned_by: str,
        action: str,
        previous_mentor_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        hist_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO assignment_history (
            id, aspirant_id, mentor_id, mentor_role, assigned_by,
            action, previous_mentor_id, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hist_id, aspirant_id, mentor_id, mentor_role, assigned_by,
            action, previous_mentor_id, notes, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "id": hist_id,
            "aspirant_id": aspirant_id,
            "mentor_id": mentor_id,
            "mentor_role": mentor_role,
            "assigned_by": assigned_by,
            "action": action,
            "previous_mentor_id": previous_mentor_id,
            "notes": notes,
            "created_at": now_iso
        }

    def list_assignment_history(self, aspirant_id: Optional[str] = None, mentor_id: Optional[str] = None) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        if aspirant_id:
            cur.execute("""
            SELECT ah.*, p.full_name as aspirant_name, m.full_name as mentor_name,
                   prev.full_name as previous_mentor_name
            FROM assignment_history ah
            JOIN profiles p ON ah.aspirant_id = p.id
            JOIN profiles m ON ah.mentor_id = m.id
            LEFT JOIN profiles prev ON ah.previous_mentor_id = prev.id
            WHERE ah.aspirant_id = ?
            ORDER BY ah.created_at DESC
            """, (aspirant_id,))
        elif mentor_id:
            cur.execute("""
            SELECT ah.*, p.full_name as aspirant_name, m.full_name as mentor_name,
                   prev.full_name as previous_mentor_name
            FROM assignment_history ah
            JOIN profiles p ON ah.aspirant_id = p.id
            JOIN profiles m ON ah.mentor_id = m.id
            LEFT JOIN profiles prev ON ah.previous_mentor_id = prev.id
            WHERE ah.mentor_id = ? OR ah.previous_mentor_id = ?
            ORDER BY ah.created_at DESC
            """, (mentor_id, mentor_id))
        else:
            cur.execute("""
            SELECT ah.*, p.full_name as aspirant_name, m.full_name as mentor_name,
                   prev.full_name as previous_mentor_name
            FROM assignment_history ah
            JOIN profiles p ON ah.aspirant_id = p.id
            JOIN profiles m ON ah.mentor_id = m.id
            LEFT JOIN profiles prev ON ah.previous_mentor_id = prev.id
            ORDER BY ah.created_at DESC
            """)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def escalate_overdue_help_requests(self) -> int:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE help_requests
        SET status = 'ESCALATED',
            escalated_at = ?,
            escalation_reason = 'Automatically escalated after 7 days without resolution.',
            updated_at = ?
        WHERE status IN ('OPEN', 'IN_PROGRESS')
          AND datetime(created_at) <= datetime('now', '-7 days')
        """, (now_iso, now_iso))
        count = cur.rowcount
        conn.commit()
        conn.close()
        return max(0, count)

    # ── SCHEME RELEASES (Guide Governance) ──
    def create_or_update_scheme_release(
        self,
        aspirant_id: str,
        guide_id: str,
        scheme_id: str,
        guide_recommendation: str,
        guide_note: str = "",
        eligibility_summary: str = ""
    ) -> Dict:
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        now_iso = datetime.now(timezone.utc).isoformat()
        rel_id = str(uuid.uuid4())

        cur.execute("""
        INSERT INTO scheme_releases (
            id, aspirant_id, guide_id, scheme_id, status, guide_note,
            guide_recommendation, eligibility_summary, released_at, released_by,
            withdrawn_at, withdrawn_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'RELEASED', ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
        ON CONFLICT(aspirant_id, scheme_id) DO UPDATE SET
            guide_id = excluded.guide_id,
            status = 'RELEASED',
            guide_note = excluded.guide_note,
            guide_recommendation = excluded.guide_recommendation,
            eligibility_summary = excluded.eligibility_summary,
            released_at = excluded.released_at,
            released_by = excluded.released_by,
            withdrawn_at = NULL,
            withdrawn_by = NULL,
            updated_at = excluded.updated_at
        """, (
            rel_id, aspirant_id, guide_id, scheme_id, guide_note,
            guide_recommendation, eligibility_summary, now_iso, guide_id,
            now_iso, now_iso
        ))
        conn.commit()

        cur.execute("SELECT * FROM scheme_releases WHERE aspirant_id = ? AND scheme_id = ?", (aspirant_id, scheme_id))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else {}

    def withdraw_scheme_release(self, aspirant_id: str, scheme_id: str, guide_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        UPDATE scheme_releases
        SET status = 'WITHDRAWN',
            withdrawn_at = ?,
            withdrawn_by = ?,
            updated_at = ?
        WHERE aspirant_id = ? AND scheme_id = ?
        """, (now_iso, guide_id, now_iso, aspirant_id, scheme_id))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def get_released_schemes_for_aspirant(self, aspirant_id: str) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
        SELECT s.*, r.id as release_id, r.guide_id, r.guide_recommendation, r.guide_note,
               r.released_at, r.status as release_status, g.full_name as guide_name
        FROM scheme_releases r
        JOIN schemes s ON r.scheme_id = s.id
        LEFT JOIN profiles g ON r.guide_id = g.id
        WHERE r.aspirant_id = ? AND r.status = 'RELEASED' AND s.is_active = 1
        ORDER BY r.released_at DESC
        """, (aspirant_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["sectors"] = json.loads(d["sectors"]) if d.get("sectors") else []
            d["eligibility"] = json.loads(d["eligibility"]) if d.get("eligibility") else []
            d["terms"] = json.loads(d["terms"]) if d.get("terms") else []
            # STRICTLY STRIP GUIDE-ONLY PRIVATE INTELLIGENCE FOR ASPIRANT
            d["hidden_agenda"] = []
            d["red_flags"] = []
            d["application_prompt"] = ""
            res.append(d)
        return res

    def get_scheme_releases_for_guide(self, guide_id: str, aspirant_id: Optional[str] = None) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        if aspirant_id:
            cur.execute("""
            SELECT r.*, s.name as scheme_name, s.agency as scheme_agency, s.amount as scheme_amount,
                   p.full_name as aspirant_name, p.email as aspirant_email
            FROM scheme_releases r
            JOIN schemes s ON r.scheme_id = s.id
            JOIN profiles p ON r.aspirant_id = p.id
            WHERE r.guide_id = ? AND r.aspirant_id = ?
            ORDER BY r.updated_at DESC
            """, (guide_id, aspirant_id))
        else:
            cur.execute("""
            SELECT r.*, s.name as scheme_name, s.agency as scheme_agency, s.amount as scheme_amount,
                   p.full_name as aspirant_name, p.email as aspirant_email
            FROM scheme_releases r
            JOIN schemes s ON r.scheme_id = s.id
            JOIN profiles p ON r.aspirant_id = p.id
            WHERE r.guide_id = ?
            ORDER BY r.updated_at DESC
            """, (guide_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_scheme_release(self, aspirant_id: str, scheme_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM scheme_releases WHERE aspirant_id = ? AND scheme_id = ?", (aspirant_id, scheme_id))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    # ── SCHEMES ──
    def list_schemes(self, search: str = "", category: str = "ALL", stage: str = "ALL", sector: str = "ALL", active_only: bool = True) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        query = "SELECT * FROM schemes WHERE 1=1"
        params = []

        if active_only:
            query += " AND is_active = 1"

        if search:
            query += " AND (LOWER(name) LIKE ? OR LOWER(agency) LIKE ? OR LOWER(description) LIKE ? OR LOWER(brief) LIKE ?)"
            s_param = f"%{search.lower()}%"
            params.extend([s_param, s_param, s_param, s_param])

        if category and category != "ALL":
            query += " AND category_type = ?"
            params.append(category)

        if stage and stage != "ALL":
            query += " AND stage = ?"
            params.append(stage)

        try:
            cur.execute(query + " ORDER BY COALESCE(display_order, 9999) ASC, name ASC", params)
        except Exception:
            try:
                cur.execute(query + " ORDER BY rowid ASC", params)
            except Exception:
                cur.execute(query + " ORDER BY name ASC", params)

        rows = cur.fetchall()
        conn.close()

        res = []
        for r in rows:
            d = dict(r)
            d["sectors"] = json.loads(d["sectors"]) if d.get("sectors") else []
            d["eligibility"] = json.loads(d["eligibility"]) if d.get("eligibility") else []
            d["terms"] = json.loads(d["terms"]) if d.get("terms") else []
            d["hidden_agenda"] = json.loads(d["hidden_agenda"]) if d.get("hidden_agenda") else []
            d["red_flags"] = json.loads(d["red_flags"]) if d.get("red_flags") else []
            d["is_active"] = bool(d.get("is_active", 1))
            # Sector filter in memory if specified
            if sector and sector != "ALL":
                sec_lower = sector.lower()
                if not any(sec_lower in str(s).lower() for s in d["sectors"]) and "all sectors" not in [str(s).lower() for s in d["sectors"]]:
                    continue
            res.append(d)
        return res

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM schemes WHERE id = ? OR source_id = ?", (scheme_id, scheme_id))
        row = cur.fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        d["sectors"] = json.loads(d["sectors"]) if d.get("sectors") else []
        d["eligibility"] = json.loads(d["eligibility"]) if d.get("eligibility") else []
        d["terms"] = json.loads(d["terms"]) if d.get("terms") else []
        d["hidden_agenda"] = json.loads(d["hidden_agenda"]) if d.get("hidden_agenda") else []
        d["red_flags"] = json.loads(d["red_flags"]) if d.get("red_flags") else []
        d["is_active"] = bool(d.get("is_active", 1))
        return d

    def upsert_scheme(self, scheme: Dict) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO schemes (
            id, source_id, name, agency, ministry, scheme_type, category_type,
            funding_type, stage, amount, brief, description, sectors, eligibility,
            terms, hidden_agenda, red_flags, process, timeline, success_rate,
            contact, state_scope, geography, application_url, last_verified,
            application_prompt, source_dataset, status, is_active, display_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            agency = excluded.agency,
            category_type = excluded.category_type,
            funding_type = excluded.funding_type,
            stage = excluded.stage,
            amount = excluded.amount,
            brief = excluded.brief,
            description = excluded.description,
            sectors = excluded.sectors,
            eligibility = excluded.eligibility,
            terms = excluded.terms,
            hidden_agenda = excluded.hidden_agenda,
            red_flags = excluded.red_flags,
            process = excluded.process,
            timeline = excluded.timeline,
            contact = excluded.contact,
            state_scope = excluded.state_scope,
            geography = excluded.geography,
            application_url = excluded.application_url,
            is_active = excluded.is_active,
            status = excluded.status,
            display_order = excluded.display_order,
            updated_at = excluded.updated_at
        """, (
            scheme["id"], scheme.get("source_id", scheme["id"]), scheme["name"],
            scheme.get("agency", ""), scheme.get("ministry", ""), scheme.get("scheme_type", "Grant"),
            scheme.get("category_type", "Central Govt"), scheme.get("funding_type", "Grant"),
            scheme.get("stage", "Pre-Seed / Seed"), scheme.get("amount", ""), scheme.get("brief", ""),
            scheme.get("description", ""), json.dumps(scheme.get("sectors", [])),
            json.dumps(scheme.get("eligibility", [])), json.dumps(scheme.get("terms", [])),
            json.dumps(scheme.get("hidden_agenda", [])), json.dumps(scheme.get("red_flags", [])),
            scheme.get("process", ""), scheme.get("timeline", ""), scheme.get("success_rate", ""),
            scheme.get("contact", ""), scheme.get("state_scope", "All India"), scheme.get("geography", "National"),
            scheme.get("application_url", ""), scheme.get("last_verified", "August 2026"),
            scheme.get("application_prompt", ""), scheme.get("source_dataset", "Founder AI Digital Playbook 2026"),
            scheme.get("status", "active"), 1 if scheme.get("is_active", True) else 0,
            scheme.get("display_order", 9999),
            now_iso, now_iso
        ))
        conn.commit()
        conn.close()
        return True

    def delete_scheme(self, scheme_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM schemes WHERE id = ? OR source_id = ?", (scheme_id, scheme_id))
        conn.commit()
        conn.close()
        return True

    # ── ACTIVITY LOG ──
    def log_activity(self, user_id: Optional[str], action: str, entity: str, entity_id: Optional[str] = None, details: Optional[Dict] = None):
        conn = self._get_conn()
        cur = conn.cursor()
        import uuid
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("""
        INSERT INTO activity_log (id, user_id, action, entity, entity_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), user_id, action, entity, entity_id, json.dumps(details or {}), now_iso))
        conn.commit()
        conn.close()

# Singleton accessor
_LOCAL_DB_INSTANCE = None
def get_local_db() -> LocalDatabase:
    global _LOCAL_DB_INSTANCE
    if _LOCAL_DB_INSTANCE is None:
        _LOCAL_DB_INSTANCE = LocalDatabase()
    return _LOCAL_DB_INSTANCE
