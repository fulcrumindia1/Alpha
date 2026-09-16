import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from services.auth import get_supabase_admin_client
from services.local_db import get_local_db

print("=== CLEANING HELP / SUPPORT REQUESTS FROM JOURNEY EVENTS ===")

# Supabase cleanup
admin_client = get_supabase_admin_client()
if admin_client:
    try:
        res = admin_client.table("journey_events").delete().in_("event_type", ["help_requested", "help_resolved"]).execute()
        count = len(res.data) if res.data else 0
        print(f"Supabase: Deleted {count} help_requested/help_resolved records from journey_events.")
    except Exception as e:
        print(f"Supabase delete error: {e}")

# SQLite cleanup
try:
    db = get_local_db()
    conn = db._get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM journey_events WHERE event_type IN ('help_requested', 'help_resolved')")
    deleted_sql = cur.rowcount
    conn.commit()
    conn.close()
    print(f"SQLite: Deleted {deleted_sql} help_requested/help_resolved records from journey_events.")
except Exception as e:
    print(f"SQLite delete error: {e}")

print("=== CLEANUP COMPLETED ===")
