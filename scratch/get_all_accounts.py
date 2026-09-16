import sys, os
sys.path.insert(0, os.path.abspath('.'))

from services.auth import get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

print("Current Backend:", get_data_backend())

# Query Supabase
admin = get_supabase_admin_client()
if admin:
    print("=== SUPABASE PROFILES ===")
    res = admin.table("profiles").select("id, email, role, full_name, profile_data").execute()
    for p in res.data or []:
        pd = p.get("profile_data") or {}
        b_name = pd.get("business", {}).get("business_name") if isinstance(pd, dict) else ""
        print(f"Role: {p.get('role'):<10} | Name: {p.get('full_name'):<20} | Email: {p.get('email'):<30} | Biz: {b_name}")

    # Let's also check auth.users to see if passwords or temp passwords or accounts exist
    print("\n=== SUPABASE AUTH USERS ===")
    try:
        auth_users = admin.auth.admin.list_users()
        for u in auth_users:
            meta = u.user_metadata or {}
            print(f"Auth Email: {u.email:<30} | Role: {meta.get('role', ''):<10} | Name: {meta.get('full_name', '')}")
    except Exception as e:
        print("Could not list auth users directly:", e)

# Query SQLite
local_db = get_local_db()
conn = local_db._get_conn()
cur = conn.cursor()
print("\n=== SQLITE PROFILES ===")
cur.execute("SELECT id, email, role, full_name, password_hash FROM profiles")
for r in cur.fetchall():
    print(f"Role: {r['role']:<10} | Name: {r['full_name']:<20} | Email: {r['email']:<30} | Hash: {r['password_hash'][:15]}...")
conn.close()
