"""
scripts/supabase_backup_manager.py — Enterprise Backup & Disaster Recovery for Supabase
======================================================================================
Usage:
    # 1. Take a full backup of all Supabase data into a timestamped .zip:
    python scripts/supabase_backup_manager.py backup

    # 2. Restore data from a backup .zip back into Supabase:
    python scripts/supabase_backup_manager.py restore backups/supabase_backup_YYYY-MM-DD_HH-MM-SS.zip

    # 3. Restore data from a backup .zip into Local SQLite (if Supabase is down):
    python scripts/supabase_backup_manager.py restore-sqlite backups/supabase_backup_YYYY-MM-DD_HH-MM-SS.zip
"""

import os
import sys
import json
import csv
import shutil
import zipfile
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from services.auth import get_supabase_admin_client, get_supabase_client

BACKUP_TABLES = [
    "profiles",
    "relationships",
    "journeys",
    "journey_events",
    "help_requests",
    "notifications",
    "assignment_history",
    "schemes",
]

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))


def backup_supabase():
    """Extracts all tables and auth users from Supabase and packs them into a .zip archive."""
    print("=" * 70)
    print(" [FULCRUM-INDIA] Initiating Supabase Full Data Backup")
    print("=" * 70)

    admin = get_supabase_admin_client()
    if not admin:
        print("[ERROR] Supabase Admin Client unavailable. Check your .streamlit/secrets.toml configuration.")
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_folder = os.path.join(BACKUP_DIR, f"supabase_backup_{timestamp}")
    os.makedirs(temp_folder, exist_ok=True)

    metadata = {
        "timestamp": timestamp,
        "backup_date_iso": datetime.now().isoformat(),
        "tables": {},
        "auth_users_count": 0,
        "total_records": 0,
    }

    # 1. Backup Auth Users Metadata
    print("\n[1/3] Exporting Supabase Auth Users...")
    try:
        users = admin.auth.admin.list_users()
        auth_data = []
        for u in users:
            auth_data.append({
                "id": str(getattr(u, "id", "")),
                "email": getattr(u, "email", ""),
                "role": getattr(u, "role", ""),
                "created_at": str(getattr(u, "created_at", "")),
                "last_sign_in_at": str(getattr(u, "last_sign_in_at", "")),
                "user_metadata": getattr(u, "user_metadata", {}) or {},
            })
        auth_json_path = os.path.join(temp_folder, "auth_users.json")
        with open(auth_json_path, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2, ensure_ascii=False)
        metadata["auth_users_count"] = len(auth_data)
        print(f"  ✓ Exported {len(auth_data)} Auth users to auth_users.json")
    except Exception as e:
        print(f"  ⚠ Failed to export Auth users list: {e}")

    # 2. Backup Each Public Table
    print("\n[2/3] Exporting Database Tables (JSON + CSV)...")
    total_records = 0
    for table in BACKUP_TABLES:
        try:
            # Fetch all records without pagination limits
            records = []
            page_size = 1000
            offset = 0
            while True:
                res = admin.table(table).select("*").range(offset, offset + page_size - 1).execute()
                batch = res.data or []
                records.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size

            # Save as JSON
            table_json_path = os.path.join(temp_folder, f"{table}.json")
            with open(table_json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str, ensure_ascii=False)

            # Save as CSV if records exist
            if records:
                table_csv_path = os.path.join(temp_folder, f"{table}.csv")
                fieldnames = list(records[0].keys())
                with open(table_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in records:
                        # Serialize dicts/lists to JSON strings for CSV compatibility
                        cleaned_row = {
                            k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                            for k, v in row.items()
                        }
                        writer.writerow(cleaned_row)

            metadata["tables"][table] = len(records)
            total_records += len(records)
            print(f"  ✓ Table '{table}': {len(records)} rows")
        except Exception as e:
            print(f"  ✗ Table '{table}' error: {e}")
            metadata["tables"][table] = f"Error: {e}"

    metadata["total_records"] = total_records

    # Save metadata.json
    with open(os.path.join(temp_folder, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 3. Create ZIP Archive
    print("\n[3/3] Packaging into Compressed ZIP Archive...")
    zip_filename = f"supabase_backup_{timestamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_folder):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, temp_folder)
                zipf.write(full_path, rel_path)

    # Remove temporary unzipped directory
    shutil.rmtree(temp_folder, ignore_errors=True)

    zip_size_kb = os.path.getsize(zip_path) / 1024
    print("=" * 70)
    print(" [SUCCESS] Supabase Backup Completed Successfully!")
    print(f"  ZIP File  : {zip_path}")
    print(f"  Size      : {zip_size_kb:.1f} KB")
    print(f"  Records   : {total_records} database rows + {metadata['auth_users_count']} auth accounts")
    print("=" * 70)
    return zip_path


def restore_supabase(zip_file_path: str):
    """Restores tables from a backup .zip archive back into Supabase."""
    print("=" * 70)
    print(" [FULCRUM-INDIA] Initiating Supabase Data Restoration")
    print(f" Source ZIP: {zip_file_path}")
    print("=" * 70)

    if not os.path.exists(zip_file_path):
        print(f"[ERROR] Backup file not found: {zip_file_path}")
        return False

    admin = get_supabase_admin_client()
    if not admin:
        print("[ERROR] Supabase Admin Client unavailable. Cannot connect to Supabase.")
        return False

    # Extract ZIP to temporary folder
    temp_extract_dir = os.path.join(BACKUP_DIR, "temp_restore")
    shutil.rmtree(temp_extract_dir, ignore_errors=True)
    os.makedirs(temp_extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zipf:
            zipf.extractall(temp_extract_dir)

        # Read metadata
        meta_path = os.path.join(temp_extract_dir, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            print(f" Backup created at: {meta.get('timestamp')}")
            print(f" Total records in backup: {meta.get('total_records')}")

        # Restore tables in dependency order
        for table in BACKUP_TABLES:
            table_file = os.path.join(temp_extract_dir, f"{table}.json")
            if not os.path.exists(table_file):
                print(f" [SKIP] No file found for table '{table}'")
                continue

            with open(table_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                print(f" - Table '{table}': 0 records to restore.")
                continue

            print(f" - Restoring table '{table}' ({len(records)} records)...")
            batch_size = 100
            success_count = 0
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                try:
                    # Upsert handles existing rows gracefully without duplicate key errors
                    admin.table(table).upsert(batch, on_conflict="id").execute()
                    success_count += len(batch)
                except Exception as e:
                    print(f"   ⚠ Batch {i}-{i+len(batch)} error on '{table}': {e}")

            print(f"   ✓ Successfully upserted {success_count}/{len(records)} records into '{table}'.")

        print("=" * 70)
        print(" [SUCCESS] Supabase Restoration Finished Successfully!")
        print("=" * 70)
        return True
    finally:
        shutil.rmtree(temp_extract_dir, ignore_errors=True)


def restore_to_sqlite(zip_file_path: str):
    """Emergency offline restore: populates local SQLite if Supabase backend is unreachable."""
    print("=" * 70)
    print(" [FULCRUM-INDIA] Emergency Restoration into Local SQLite Database")
    print(f" Source ZIP: {zip_file_path}")
    print("=" * 70)

    if not os.path.exists(zip_file_path):
        print(f"[ERROR] Backup file not found: {zip_file_path}")
        return False

    from services.local_db import get_local_db
    db = get_local_db()
    conn = db._get_conn()

    temp_extract_dir = os.path.join(BACKUP_DIR, "temp_restore_sqlite")
    shutil.rmtree(temp_extract_dir, ignore_errors=True)
    os.makedirs(temp_extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file_path, "r") as zipf:
            zipf.extractall(temp_extract_dir)

        # Restore profiles
        prof_file = os.path.join(temp_extract_dir, "profiles.json")
        if os.path.exists(prof_file):
            with open(prof_file, "r", encoding="utf-8") as f:
                profs = json.load(f)
            cur = conn.cursor()
            for p in profs:
                cur.execute("""
                    INSERT OR REPLACE INTO profiles (id, email, role, full_name, phone, district, state, profile_data, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("id"),
                    p.get("email"),
                    p.get("role"),
                    p.get("full_name"),
                    p.get("phone"),
                    p.get("district"),
                    p.get("state", "Tamil Nadu"),
                    json.dumps(p.get("profile_data") or {}, ensure_ascii=False),
                    1 if p.get("is_active", True) else 0,
                    p.get("created_at"),
                    p.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(profs)} profiles into local SQLite.")

        # Restore relationships
        rel_file = os.path.join(temp_extract_dir, "relationships.json")
        if os.path.exists(rel_file):
            with open(rel_file, "r", encoding="utf-8") as f:
                rels = json.load(f)
            cur = conn.cursor()
            for r in rels:
                cur.execute("""
                    INSERT OR REPLACE INTO relationships (id, aspirant_id, guide_id, sme_id, sme_ids, guide_ids, status, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.get("id"),
                    r.get("aspirant_id"),
                    r.get("guide_id"),
                    r.get("sme_id"),
                    json.dumps(r.get("sme_ids") or []),
                    json.dumps(r.get("guide_ids") or []),
                    r.get("status", "active"),
                    r.get("notes"),
                    r.get("created_at"),
                    r.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(rels)} relationships into local SQLite.")

        # Restore journeys
        j_file = os.path.join(temp_extract_dir, "journeys.json")
        if os.path.exists(j_file):
            with open(j_file, "r", encoding="utf-8") as f:
                journeys = json.load(f)
            cur = conn.cursor()
            for j in journeys:
                cur.execute("""
                    INSERT OR REPLACE INTO journeys (id, aspirant_id, title, business_type, stage, start_date, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    j.get("id"), j.get("aspirant_id"), j.get("title"), j.get("business_type"),
                    j.get("stage", "idea"), j.get("start_date"), j.get("status", "active"),
                    j.get("created_at"), j.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(journeys)} journeys into local SQLite.")

        # Restore journey_events
        je_file = os.path.join(temp_extract_dir, "journey_events.json")
        if os.path.exists(je_file):
            with open(je_file, "r", encoding="utf-8") as f:
                events = json.load(f)
            cur = conn.cursor()
            for e in events:
                cur.execute("""
                    INSERT OR REPLACE INTO journey_events (id, journey_id, aspirant_id, actor_id, actor_role, event_type, event_data, event_date, deleted_at, deleted_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e.get("id"), e.get("journey_id"), e.get("aspirant_id"), e.get("actor_id"),
                    e.get("actor_role"), e.get("event_type"),
                    json.dumps(e.get("event_data") or {}, ensure_ascii=False) if isinstance(e.get("event_data"), (dict, list)) else e.get("event_data", "{}"),
                    e.get("event_date"), e.get("deleted_at"), e.get("deleted_by"),
                    e.get("created_at"), e.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(events)} journey events into local SQLite.")

        # Restore help_requests
        hr_file = os.path.join(temp_extract_dir, "help_requests.json")
        if os.path.exists(hr_file):
            with open(hr_file, "r", encoding="utf-8") as f:
                reqs = json.load(f)
            cur = conn.cursor()
            for hr in reqs:
                cur.execute("""
                    INSERT OR REPLACE INTO help_requests (id, aspirant_id, subject, message, priority, status, admin_response, responded_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    hr.get("id"), hr.get("aspirant_id"), hr.get("subject"), hr.get("message"),
                    hr.get("priority", "MEDIUM"), hr.get("status", "OPEN"),
                    hr.get("admin_response"), hr.get("responded_by"),
                    hr.get("created_at"), hr.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(reqs)} help requests into local SQLite.")

        # Restore schemes
        sch_file = os.path.join(temp_extract_dir, "schemes.json")
        if os.path.exists(sch_file):
            with open(sch_file, "r", encoding="utf-8") as f:
                schemes = json.load(f)
            cur = conn.cursor()
            for s in schemes:
                cur.execute("""
                    INSERT OR REPLACE INTO schemes (id, source_id, name, agency, ministry, scheme_type, category_type, funding_type, stage, amount, brief, description, process, timeline, application_url, status, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.get("id"), s.get("source_id"), s.get("name"), s.get("agency"), s.get("ministry"),
                    s.get("scheme_type"), s.get("category_type"), s.get("funding_type"), s.get("stage"),
                    s.get("amount"), s.get("brief"), s.get("description"), s.get("process"), s.get("timeline"),
                    s.get("application_url"), s.get("status", "active"), 1 if s.get("is_active", True) else 0,
                    s.get("created_at"), s.get("updated_at")
                ))
            conn.commit()
            print(f"  ✓ Restored {len(schemes)} schemes into local SQLite.")

        print("=" * 70)
        print(" [SUCCESS] Local SQLite Emergency Restoration Complete!")
        print("=" * 70)
        return True
    finally:
        conn.close()
        shutil.rmtree(temp_extract_dir, ignore_errors=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "backup":
        backup_supabase()
    elif args[0] == "restore":
        if len(args) < 2:
            print("Usage: python scripts/supabase_backup_manager.py restore <path_to_backup.zip>")
        else:
            restore_supabase(args[1])
    elif args[0] in ["restore-sqlite", "restore_sqlite"]:
        if len(args) < 2:
            print("Usage: python scripts/supabase_backup_manager.py restore-sqlite <path_to_backup.zip>")
        else:
            restore_to_sqlite(args[1])
    else:
        print(f"Unknown command: {args[0]}")
        print("Available commands: backup, restore <file.zip>, restore-sqlite <file.zip>")
