"""Migrate existing MongoDB OOH data into Neon/PostgreSQL.

Usage:
  1. Set DATABASE_URL in backend/.env to your Neon PostgreSQL URL.
  2. Set MONGODB_URI and MONGODB_DB_NAME temporarily in backend/.env for the old MongoDB database.
  3. Run: python scripts/migrate_mongodb_to_neon.py

Uploaded files are not stored in MongoDB; copy backend/app/uploads separately.
"""

from datetime import datetime
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

load_dotenv(ROOT / ".env")

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal, init_database  # noqa: E402
from app.models import OOHSite, User  # noqa: E402


def parse_dt(value):
    if isinstance(value, datetime):
        return value
    if value:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return datetime.utcnow()
    return datetime.utcnow()


def parse_date(value):
    dt = parse_dt(value)
    return dt.date()


def main():
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "adinn_ooh_tracker")
    client = MongoClient(mongodb_uri)
    old_db = client[mongodb_db_name]

    init_database()
    db = SessionLocal()
    try:
        user_id_map = {}
        for old_user in old_db.users.find().sort("id", 1):
            email = str(old_user.get("email", "")).lower()
            if not email:
                continue
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    name=old_user.get("name") or "User",
                    email=email,
                    phone=old_user.get("phone"),
                    password_hash=old_user.get("password_hash") or hash_password("ChangeMe@123"),
                    role=old_user.get("role") or "employee",
                    is_active=bool(old_user.get("is_active", True)),
                    can_crud=bool(old_user.get("can_crud", False)),
                    created_at=parse_dt(old_user.get("created_at")),
                    updated_at=parse_dt(old_user.get("updated_at")),
                )
                db.add(user)
                db.flush()
            user_id_map[int(old_user.get("id"))] = int(user.id)

        migrated = 0
        for old_site in old_db.ooh_sites.find().sort("id", 1):
            old_id = int(old_site.get("id"))
            existing = db.query(OOHSite).filter(OOHSite.id == old_id).first()
            if existing:
                continue
            docs = old_site.get("documents") or {}
            created_by = user_id_map.get(int(old_site.get("created_by_user_id", 0)))
            if not created_by:
                admin = db.query(User).filter(User.role == "admin").first()
                created_by = admin.id if admin else 1
            site = OOHSite(
                id=old_id,
                created_by_user_id=created_by,
                hoarding_location=old_site.get("hoarding_location", ""),
                landlord_location=old_site.get("landlord_location", ""),
                landlord_name=old_site.get("landlord_name", ""),
                landlord_phone=old_site.get("landlord_phone", ""),
                landlord_email=old_site.get("landlord_email"),
                secondary_contact_name=old_site.get("secondary_contact_name"),
                secondary_contact_phone=old_site.get("secondary_contact_phone"),
                height_ft=float(old_site.get("height_ft", 0) or 0),
                width_ft=float(old_site.get("width_ft", 0) or 0),
                area_sqft=float(old_site.get("area_sqft", 0) or 0),
                rental_type=old_site.get("rental_type", ""),
                advance_amount=float(old_site.get("advance_amount", 0) or 0),
                light_type=old_site.get("light_type", ""),
                side_type=old_site.get("side_type", ""),
                towards_1=old_site.get("towards_1"),
                towards_2=old_site.get("towards_2"),
                latitude=old_site.get("latitude"),
                longitude=old_site.get("longitude"),
                agreement_tenure=old_site.get("agreement_tenure", ""),
                agreement_start_date=parse_date(old_site.get("agreement_start_date")),
                agreement_end_date=parse_date(old_site.get("agreement_end_date")),
                remarks=old_site.get("remarks") or {},
                site_photo_file=docs.get("site_photo_file"),
                landlord_photo_file=docs.get("landlord_photo_file"),
                aadhaar_file=docs.get("aadhaar_file"),
                pan_file=docs.get("pan_file"),
                property_tax_file=docs.get("property_tax_file"),
                passbook_file=docs.get("passbook_file"),
                created_at=parse_dt(old_site.get("created_at")),
                updated_at=parse_dt(old_site.get("updated_at")),
            )
            db.add(site)
            migrated += 1
        db.commit()
        print(f"Migration complete. Migrated {migrated} OOH site records.")
        print("Remember: copy backend/app/uploads separately if you need old photos/documents.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
