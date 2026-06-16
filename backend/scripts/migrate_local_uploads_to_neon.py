"""Copy existing local uploaded files into Neon PostgreSQL stored_files table.

Run from backend folder after setting DATABASE_URL in .env:
    python scripts/migrate_local_uploads_to_neon.py

This does not delete local files and does not delete database records.
"""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_database  # noqa: E402
from app.models import OOHSite, StoredFile  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR") or (BASE_DIR / "app" / "uploads"))
FILE_FIELDS = [
    "site_photo_file",
    "landlord_photo_file",
    "aadhaar_file",
    "pan_file",
    "property_tax_file",
    "passbook_file",
]


def main() -> None:
    init_database()
    db = SessionLocal()
    copied = 0
    missing = 0
    skipped = 0
    try:
        for site in db.query(OOHSite).all():
            for field_name in FILE_FIELDS:
                marker = getattr(site, field_name, None)
                if not marker:
                    continue
                existing = db.query(StoredFile).filter(
                    StoredFile.site_id == int(site.id),
                    StoredFile.field_name == field_name,
                ).first()
                if existing:
                    skipped += 1
                    continue
                file_path = UPLOAD_DIR / str(marker)
                if not file_path.exists() or not file_path.is_file():
                    missing += 1
                    continue
                content = file_path.read_bytes()
                content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                db.add(StoredFile(
                    site_id=int(site.id),
                    field_name=field_name,
                    original_filename=file_path.name,
                    content_type=content_type,
                    file_size=len(content),
                    data=content,
                ))
                copied += 1
        db.commit()
    finally:
        db.close()
    print(f"Copied {copied} files to Neon. Skipped {skipped}. Missing local files {missing}.")


if __name__ == "__main__":
    main()
