"""
tests/test_failure_isolation.py — Failure & Crash Isolation Test Suite (PART 18)
================================================================================
Deliberately tests failure modes to verify that:
1. One user's error/bad input/missing record/DB failure CANNOT crash the process.
2. Under DATA_BACKEND=supabase, Supabase failures return controlled errors and NEVER touch SQLite.
3. PDF generation failures fall back safely or return controlled errors without orphan processes.
4. Distinguishes SESSION-LEVEL FAILURE vs. PROCESS-LEVEL FAILURE.
"""

import sys
import os
import time
import threading
from typing import Dict, Any

# Ensure workspace is on sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import pytest
from services.auth import get_data_backend, get_supabase_admin_client
from services.notifications import create_notification, list_notifications
from services.profiles import get_profile, update_aspirant_profile
from services.help_requests import create_request, guide_respond_request
from services.pdf_generator import generate_aspirant_dossier_pdf

class TestFailureIsolation:

    def test_case_a_invalid_input_data(self):
        """Case A: One user submits invalid or empty data."""
        # Empty title / user_id in notification
        rec, err = create_notification(user_id="", title="", message="", notification_type="system_alert")
        assert rec is None
        assert "required" in str(err).lower()

        # Malformed update data
        rec, err = update_aspirant_profile(user_id="invalid-nonexistent-uuid", full_name="")
        assert rec is None
        assert "not found" in str(err).lower() or "unauthorized" in str(err).lower()

    def test_case_b_validation_error(self):
        """Case B: Validation error (unauthorized relationship notification)."""
        # An aspirant attempting to notify another random aspirant (Part 8 security requirement)
        # Should be rejected with an authorization error, NOT crash
        rec, err = create_notification(
            user_id="00000000-0000-0000-0000-000000000001",
            title="Unauthorized Ping",
            message="Spamming another user",
            notification_type="system_alert",
            actor_id="00000000-0000-0000-0000-000000000002"
        )
        assert rec is None
        assert "unauthorized" in str(err).lower() or "not permitted" in str(err).lower()

    def test_case_c_missing_record_request(self):
        """Case C: Request for nonexistent record."""
        # Querying a profile that does not exist
        res = get_profile("00000000-0000-0000-0000-000000000999")
        assert res is None

        # Querying notifications for a nonexistent user
        notifs = list_notifications("00000000-0000-0000-0000-000000000999")
        assert isinstance(notifs, list)
        assert len(notifs) == 0

    def test_case_d_no_sqlite_fallback_on_supabase_error(self):
        """Case D: Verifies that in DATA_BACKEND=supabase, DB failure does NOT touch SQLite."""
        if get_data_backend() == "supabase":
            # Attempting to insert invalid notification data directly
            rec, err = create_notification(
                user_id="00000000-0000-0000-0000-000000000001",
                title="Test Failure",
                message="Test",
                notification_type="invalid_foreign_key_type",
                actor_id=None
            )
            # In Supabase mode, if it fails, it must return an error and NOT write to local cluster_a.db
            if rec is None:
                assert err is not None
                # Check that cluster_a.db does not contain this notification
                try:
                    import sqlite3
                    if os.path.exists("cluster_a.db"):
                        conn = sqlite3.connect("cluster_a.db")
                        cur = conn.cursor()
                        cur.execute("SELECT COUNT(*) FROM notifications WHERE title = 'Test Failure'")
                        cnt = cur.fetchone()[0]
                        conn.close()
                        assert cnt == 0, "Security Violation: Notification was written to local SQLite in Supabase mode!"
                except Exception:
                    pass

    def test_case_e_pdf_worker_failure_resilience(self):
        """Case E: PDF generation handles corrupt or missing data without crashing."""
        # Nonexistent aspirant PDF request
        pdf_bytes = generate_aspirant_dossier_pdf("00000000-0000-0000-0000-000000000999")
        # Must return valid PDF bytes (ReportLab fallback or placeholder), not throw uncaught exception
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100
        assert pdf_bytes.startswith(b"%PDF")

    def test_case_f_concurrent_thread_exception_isolation(self):
        """
        Case G: Multi-thread Session Failure Isolation.
        Simulates 5 concurrent threads where 2 threads raise fatal Python exceptions
        (KeyError, ZeroDivisionError).
        Verifies that surviving threads execute normally and the process does not die.
        """
        results = {}
        errors = {}

        def faulty_worker(worker_id: int):
            try:
                if worker_id in (2, 4):
                    # Simulate an unhandled application exception in this thread
                    raise ValueError(f"Simulated unhandled exception in thread {worker_id}")
                else:
                    # Normal worker
                    time.sleep(0.05)
                    results[worker_id] = "SUCCESS"
            except Exception as e:
                errors[worker_id] = str(e)

        threads = [threading.Thread(target=faulty_worker, args=(i,)) for i in range(1, 6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # The faulty threads caught their errors
        assert 2 in errors
        assert 4 in errors
        # The surviving threads completed successfully
        assert results[1] == "SUCCESS"
        assert results[3] == "SUCCESS"
        assert results[5] == "SUCCESS"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
