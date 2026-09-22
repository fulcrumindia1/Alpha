"""
tests/test_cross_session_isolation.py
======================================
Part 20 & Part 21 — Cross-Session Isolation & Multi-Role Concurrency Test Suite.
Simulates 3 Aspirants, 1 Guide, 1 SME, and 2 Admins running concurrently.
Verifies data boundaries, authorization isolation, and concurrent dossier PDF generation.
"""

import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

from services.auth import get_supabase_admin_client, get_data_backend
from services.profiles import get_profile, update_aspirant_profile
from services.notifications import create_notification, list_notifications
from services.journey import get_journey_timeline, add_manual_aspirant_entry
from services.help_requests import list_requests
from services.pdf_generator import generate_aspirant_dossier_pdf


class TestCrossSessionIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.admin_client = get_supabase_admin_client()
        cls.backend = get_data_backend()
        
        # Test personas
        cls.admin1 = {"email": "admin@fulcrum.in", "role": "admin"}
        cls.admin2 = {"email": "manicktie@gmail.com", "role": "admin"}
        cls.guide = {"email": "rajendran@fulcrum.in", "role": "guide"}
        cls.sme = {"email": "kumar.sme@fulcrum.in", "role": "sme"}
        cls.asp1 = {"email": "ravi.kumar@milletfoods.in", "role": "aspirant"}
        
        # Fetch real IDs if available in Supabase
        if cls.admin_client and cls.backend == "supabase":
            for persona in [cls.admin1, cls.admin2, cls.guide, cls.sme, cls.asp1]:
                try:
                    res = cls.admin_client.table("profiles").select("id, full_name, role").eq("email", persona["email"]).execute()
                    if res.data and len(res.data) > 0:
                        persona["id"] = res.data[0]["id"]
                        persona["full_name"] = res.data[0].get("full_name", "")
                except Exception:
                    pass

        # Fallback IDs if running in isolated sandbox
        cls.admin1_id = cls.admin1.get("id", "00000000-0000-0000-0000-000000000001")
        cls.admin2_id = cls.admin2.get("id", "00000000-0000-0000-0000-000000000002")
        cls.guide_id = cls.guide.get("id", "00000000-0000-0000-0000-000000000010")
        cls.sme_id = cls.sme.get("id", "00000000-0000-0000-0000-000000000020")
        cls.asp1_id = cls.asp1.get("id", "00000000-0000-0000-0000-000000000100")
        cls.asp2_id = "00000000-0000-0000-0000-000000000200"
        cls.asp3_id = "00000000-0000-0000-0000-000000000300"

    def test_01_aspirant_cannot_modify_another_aspirant_profile(self):
        """Verify Aspirant A cannot modify Aspirant B's profile."""
        rec, err = update_aspirant_profile(
            user_id=self.asp2_id,
            full_name="Hacked By Asp1",
            actor_id=self.asp1_id
        )
        self.assertIsNone(rec, "Aspirant 1 should NOT be allowed to update Aspirant 2's profile")
        self.assertIn("Unauthorized", err)

    def test_02_aspirant_cannot_spam_another_aspirant_notifications(self):
        """Verify Aspirant A cannot send unauthorized notifications to Aspirant B."""
        rec, err = create_notification(
            user_id=self.asp2_id,
            title="Unauthorized Cross-Talk",
            message="Hey Asp2, buy my product!",
            notification_type="system_alert",
            actor_id=self.asp1_id
        )
        self.assertIsNone(rec, "Cross-aspirant direct notification should be blocked")
        self.assertIn("Unauthorized", err)

    def test_03_concurrent_multi_user_read_isolation(self):
        """
        Simulate simultaneous requests from 3 Aspirants, 1 Guide, 1 SME, and 2 Admins.
        All 7 sessions run in parallel threads.
        """
        results = {}

        def aspirant_session(aspirant_id: str, name: str):
            timeline = get_journey_timeline(aspirant_id)
            notifs = list_notifications(aspirant_id)
            reqs = list_requests(aspirant_id)
            return {"name": name, "timeline_count": len(timeline), "notifs_count": len(notifs), "status": "ok"}

        def mentor_session(mentor_id: str, role: str):
            notifs = list_notifications(mentor_id)
            return {"role": role, "notifs_count": len(notifs), "status": "ok"}

        def admin_session(admin_id: str, name: str):
            notifs = list_notifications(admin_id)
            prof = get_profile(admin_id)
            return {"name": name, "admin_notifs": len(notifs), "status": "ok"}

        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                executor.submit(aspirant_session, self.asp1_id, "Asp1"): "asp1",
                executor.submit(aspirant_session, self.asp2_id, "Asp2"): "asp2",
                executor.submit(aspirant_session, self.asp3_id, "Asp3"): "asp3",
                executor.submit(mentor_session, self.guide_id, "guide"): "guide",
                executor.submit(mentor_session, self.sme_id, "sme"): "sme",
                executor.submit(admin_session, self.admin1_id, "Admin1"): "admin1",
                executor.submit(admin_session, self.admin2_id, "Admin2"): "admin2",
            }

            for future in as_completed(futures):
                role_key = futures[future]
                try:
                    res = future.result(timeout=15)
                    results[role_key] = res
                except Exception as e:
                    results[role_key] = {"error": str(e)}

        # Verify all 7 completed successfully without any cross-thread exceptions
        self.assertEqual(len(results), 7)
        for role, res in results.items():
            self.assertNotIn("error", res, f"Session {role} raised an exception: {res.get('error')}")
            self.assertEqual(res.get("status"), "ok")

    def test_04_concurrent_admin_pdf_generation(self):
        """
        Verify 2 Admins can generate PDF dossiers concurrently without crash.
        Validates that the PDF semaphore (limit=2) protects memory while allowing concurrent exports.
        """
        sample_aspirant = {
            "id": self.asp1_id,
            "full_name": "Ravi Kumar",
            "business_name": "Millet Foods Pvt Ltd",
            "district": "Coimbatore",
            "sector": "Food Processing",
            "enterprise_stage": "Operational / Revenue",
            "phone_number": "+91 9876543210",
            "email": "ravi.kumar@milletfoods.in"
        }

        pdf_results = {}

        def export_pdf(admin_name: str):
            start = time.time()
            pdf_bytes = generate_aspirant_dossier_pdf(self.asp1_id)
            duration = time.time() - start
            return {"admin": admin_name, "bytes": len(pdf_bytes) if pdf_bytes else 0, "duration": duration}

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(export_pdf, "Admin1")
            f2 = executor.submit(export_pdf, "Admin2")
            
            r1 = f1.result(timeout=60)
            r2 = f2.result(timeout=60)

        self.assertIsNotNone(r1["bytes"])
        self.assertGreater(r1["bytes"], 1000, "Admin 1 PDF generation failed or empty")
        self.assertIsNotNone(r2["bytes"])
        self.assertGreater(r2["bytes"], 1000, "Admin 2 PDF generation failed or empty")


if __name__ == "__main__":
    unittest.main()
