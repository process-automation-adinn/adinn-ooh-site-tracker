"""Migrate existing ADINN OOH Site Tracker SQLite data to MongoDB.

Usage from backend folder:
    python scripts/migrate_sqlite_to_mongodb.py --sqlite ooh_tracker.db

Optional:
    python scripts/migrate_sqlite_to_mongodb.py --sqlite ooh_tracker.db --mongodb-uri mongodb://localhost:27017 --db-name adinn_ooh_tracker

The script copies:
- users
- ooh_sites
- landlord document file paths embedded inside each site document
- counters are updated so new MongoDB records continue after the highest migrated ID

It does not copy actual uploaded files. Keep/copy backend/app/uploads separately.
"""

from __future__ import annotations

import argparse
from datetime import datetime, time
import json
from pathlib import Path
import sqlite3
from typing import Any

from pymongo import MongoClient


def parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text[:26], fmt)
            if fmt == "%Y-%m-%d":
                return datetime.combine(parsed.date(), time.min)
            return parsed
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.utcnow()


def parse_date_as_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.combine(datetime.fromisoformat(str(value)[:10]).date(), time.min)
    except ValueError:
        return None


def parse_remarks(value: Any) -> dict[str, str]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v).strip() for k, v in data.items() if str(v).strip()}


def has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="ooh_tracker.db", help="Path to existing SQLite database")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017", help="MongoDB connection string")
    parser.add_argument("--db-name", default="adinn_ooh_tracker", help="MongoDB database name")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    mongo = MongoClient(args.mongodb_uri)[args.db_name]

    users = list(cursor.execute("SELECT * FROM users"))
    max_user_id = 0
    for row in users:
        data = row_to_dict(row)
        user_id = int(data["id"])
        max_user_id = max(max_user_id, user_id)
        user_doc = {
            "id": user_id,
            "name": data.get("name") or "",
            "email": (data.get("email") or "").lower(),
            "phone": data.get("phone"),
            "password_hash": data.get("password_hash") or "",
            "role": data.get("role") or "employee",
            "is_active": bool(data.get("is_active", True)),
            "can_crud": bool(data.get("can_crud", False)) if has_column(cursor, "users", "can_crud") else False,
            "created_at": parse_datetime(data.get("created_at")),
        }
        if user_doc["role"] == "admin":
            user_doc["can_crud"] = True
        mongo.users.update_one({"id": user_id}, {"$set": user_doc}, upsert=True)

    cursor.execute("SELECT * FROM ooh_sites")
    sites = cursor.fetchall()
    max_site_id = 0
    for row in sites:
        data = row_to_dict(row)
        site_id = int(data["id"])
        max_site_id = max(max_site_id, site_id)
        docs = {}
        cursor.execute("SELECT * FROM landlord_documents WHERE site_id = ?", (site_id,))
        doc_row = row_to_dict(cursor.fetchone())
        for key in ["site_photo_file", "landlord_photo_file", "aadhaar_file", "pan_file", "property_tax_file", "passbook_file"]:
            if doc_row.get(key):
                docs[key] = doc_row.get(key)
        if doc_row:
            docs["created_at"] = parse_datetime(doc_row.get("created_at"))
            docs["updated_at"] = parse_datetime(doc_row.get("updated_at"))

        site_doc = {
            "id": site_id,
            "created_by_user_id": int(data.get("created_by_user_id")),
            "hoarding_location": data.get("hoarding_location") or "",
            "landlord_location": data.get("landlord_location") or "",
            "landlord_name": data.get("landlord_name") or "",
            "landlord_phone": data.get("landlord_phone") or "",
            "landlord_email": data.get("landlord_email"),
            "secondary_contact_name": data.get("secondary_contact_name"),
            "secondary_contact_phone": data.get("secondary_contact_phone"),
            "height_ft": float(data.get("height_ft") or 0),
            "width_ft": float(data.get("width_ft") or 0),
            "area_sqft": float(data.get("area_sqft") or 0),
            "rental_type": data.get("rental_type") or "",
            "advance_amount": float(data.get("advance_amount") or 0),
            "light_type": data.get("light_type") or "",
            "side_type": data.get("side_type") or "",
            "towards_1": data.get("towards_1"),
            "towards_2": data.get("towards_2"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "agreement_tenure": data.get("agreement_tenure") or "",
            "agreement_start_date": parse_date_as_datetime(data.get("agreement_start_date")),
            "agreement_end_date": parse_date_as_datetime(data.get("agreement_end_date")),
            "remarks": parse_remarks(data.get("remarks_json")) if has_column(cursor, "ooh_sites", "remarks_json") else {},
            "documents": docs,
            "created_at": parse_datetime(data.get("created_at")),
            "updated_at": parse_datetime(data.get("updated_at")),
        }
        mongo.ooh_sites.update_one({"id": site_id}, {"$set": site_doc}, upsert=True)

    mongo.counters.update_one({"_id": "users"}, {"$max": {"seq": max_user_id}}, upsert=True)
    mongo.counters.update_one({"_id": "ooh_sites"}, {"$max": {"seq": max_site_id}}, upsert=True)
    mongo.users.create_index("email", unique=True)
    mongo.users.create_index("id", unique=True)
    mongo.ooh_sites.create_index("id", unique=True)
    mongo.ooh_sites.create_index("created_by_user_id")

    print(f"Migrated {len(users)} users and {len(sites)} OOH site records to MongoDB database '{args.db_name}'.")
    print("Reminder: copy backend/app/uploads to the new project if uploaded files are needed.")


if __name__ == "__main__":
    main()
