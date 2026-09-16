import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from datetime import datetime, timezone
from services.auth import get_supabase_admin_client

def main():
    admin = get_supabase_admin_client()
    if not admin:
        print("[ERROR] Supabase admin client not available.")
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    accounts = [
        {
            "email": "admin@fulcrum.in",
            "password": "Admin@123",
            "role": "admin",
            "full_name": "Fulcrum Administrator",
            "phone": "9876543213",
            "district": "Chennai",
            "profile_data": {}
        },
        {
            "email": "rajendran@fulcrum.in",
            "password": "Welcome@2026",
            "role": "guide",
            "full_name": "Rajendran Natarajan",
            "phone": "9840123456",
            "district": "Chennai",
            "profile_data": {
                "expertise": "Enterprise Strategy, Agribusiness Scaling",
                "bio": "Senior Enterprise Guide with 15+ years experience mentoring MSMEs.",
                "industry": "Agribusiness",
                "temp_password_issued": True
            }
        },
        {
            "email": "kumar.sme@fulcrum.in",
            "password": "Welcome@2026",
            "role": "sme",
            "full_name": "Kumar S.",
            "phone": "9840654321",
            "district": "Madurai",
            "profile_data": {
                "expertise": "GST, Indirect Taxation & FSSAI Compliance",
                "bio": "Specialized Chartered Accountant & Compliance Consultant.",
                "industry": "Taxation & Regulatory",
                "temp_password_issued": True
            }
        },
        {
            "email": "ravi.kumar@milletfoods.in",
            "password": "Aspirant@123",
            "role": "aspirant",
            "full_name": "Ravi Kumar",
            "phone": "9876543210",
            "district": "Madurai",
            "profile_data": {
                "personal": {"full_name": "Ravi Kumar", "email": "ravi.kumar@milletfoods.in", "phone": "9876543210", "district": "Madurai", "state": "Tamil Nadu", "gender": "Male", "dob": "15-08-1995", "address": "12 Main Road, Madurai"},
                "professional": {"education": "B.Sc Agriculture", "experience_years": 4, "skills": ["Food Processing", "Supply Chain", "Retail"], "current_status": "Full-time Founder", "experience": "3 years in food manufacturing", "certifications": "FSSAI Basic, MSME EDI Training"},
                "business": {"business_name": "Organic Millet Foods", "business_type": "Manufacturing", "sector": "Food Processing", "stage": "Pre-Seed / Seed", "investment_bracket": "10L-25L", "revenue": "₹12,00,000 / year", "employee_count": 3, "description": "Nutritional value-added millet products for urban families."},
                "demographics": {"district": "Madurai", "state": "Tamil Nadu", "founder_category": "OBC", "social_category": "OBC", "gender": "Male", "is_dpiit_recognized": True, "is_startuptn_registered": True, "is_women_led": False}
            }
        }
    ]

    existing_users = {u.email.lower(): u for u in admin.auth.admin.list_users()}
    user_ids = {}

    for acc in accounts:
        email = acc["email"].lower()
        role = acc["role"]
        if email in existing_users:
            u_id = existing_users[email].id
            print(f"[EXISTS] {email} -> {u_id}")
            try:
                admin.auth.admin.update_user_by_id(u_id, {
                    "password": acc["password"],
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": acc["full_name"],
                        "role": role,
                        "district": acc["district"],
                        "phone": acc["phone"]
                    }
                })
            except Exception as e:
                print(f"  Warning updating {email}: {e}")
            user_ids[role] = u_id
        else:
            try:
                res = admin.auth.admin.create_user({
                    "email": email,
                    "password": acc["password"],
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": acc["full_name"],
                        "role": role,
                        "district": acc["district"],
                        "phone": acc["phone"]
                    }
                })
                u_id = res.user.id
                print(f"[CREATED] {email} ({role}) -> {u_id}")
                user_ids[role] = u_id
            except Exception as e:
                print(f"[ERROR] Creating {email}: {e}")
                continue

        try:
            profile_record = {
                "id": user_ids[role],
                "email": email,
                "role": role,
                "full_name": acc["full_name"],
                "phone": acc["phone"],
                "district": acc["district"],
                "state": "Tamil Nadu",
                "profile_data": acc["profile_data"],
                "is_active": True,
                "updated_at": now_iso
            }
            admin.table("profiles").upsert(profile_record, on_conflict="id").execute()
            print(f"  [PROFILE SYNCED] {email}")
        except Exception as e:
            print(f"  [PROFILE ERROR] {email}: {e}")

    asp_id = user_ids.get("aspirant")
    admin_id = user_ids.get("admin")
    guide_id = user_ids.get("guide")
    sme_id = user_ids.get("sme")

    if asp_id:
        try:
            admin.table("journeys").upsert({
                "aspirant_id": asp_id,
                "title": "Venture Formation & Scale Journey",
                "business_type": "Manufacturing",
                "stage": "Pre-Seed / Seed",
                "status": "active",
                "updated_at": now_iso
            }, on_conflict="aspirant_id").execute()
            print("  [JOURNEY SYNCED]")
        except Exception as e:
            print(f"  [JOURNEY ERROR] {e}")

        if guide_id or sme_id:
            try:
                admin.table("relationships").upsert({
                    "aspirant_id": asp_id,
                    "guide_id": guide_id,
                    "sme_id": sme_id,
                    "assigned_by": admin_id,
                    "status": "active",
                    "notes": "Dedicated Enterprise Mentor and Compliance SME assigned.",
                    "updated_at": now_iso
                }, on_conflict="aspirant_id").execute()
                print("  [RELATIONSHIP SYNCED]")
            except Exception as e:
                print(f"  [RELATIONSHIP ERROR] {e}")

    print("\n✅ All test accounts seeded and synced successfully!")

if __name__ == "__main__":
    main()
