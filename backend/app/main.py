from datetime import date, datetime
import os
import json
from pathlib import Path
import shutil
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
import io
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import create_token, get_current_user, hash_password, require_admin, verify_password
from .database import get_db, init_database, ping_database
from .models import OOHSite, User
from .schemas import CrudPermissionUpdate, LoginRequest, SiteOut, TokenResponse, UserCreate, UserOut, UserUpdate

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR") or (BASE_DIR / "app" / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ADINN OOH Site Tracker API", version="3.0.0-neon-postgres")


def get_allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

ALLOWED_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

SECTION_REMARK_LABELS = {
    "site_location": "Site Location",
    "landlord_contact": "Landlord Contact Details",
    "size_rental_display": "Size, Rental & Display",
    "documents": "Photos & Documents",
    "gps_agreement": "GPS & Agreement",
}


def now_utc() -> datetime:
    return datetime.utcnow()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def init_db():
    init_database()
    db = next(get_db())
    try:
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@adinn.com").strip().lower()
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "Admin@123")
        admin_name = os.getenv("SEED_ADMIN_NAME", "ADINN Admin").strip() or "ADINN Admin"

        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            db.add(
                User(
                    name=admin_name,
                    email=admin_email,
                    phone="",
                    password_hash=hash_password(admin_password),
                    role="admin",
                    is_active=True,
                    can_crud=True,
                    created_at=now_utc(),
                    updated_at=now_utc(),
                )
            )
            db.commit()

        if env_bool("CREATE_DEMO_EMPLOYEE", True):
            employee_email = os.getenv("DEMO_EMPLOYEE_EMAIL", "employee@adinn.com").strip().lower()
            employee_password = os.getenv("DEMO_EMPLOYEE_PASSWORD", "Employee@123")
            employee_name = os.getenv("DEMO_EMPLOYEE_NAME", "Field Employee").strip() or "Field Employee"
            employee = db.query(User).filter(User.email == employee_email).first()
            if not employee:
                db.add(
                    User(
                        name=employee_name,
                        email=employee_email,
                        phone="",
                        password_hash=hash_password(employee_password),
                        role="employee",
                        is_active=True,
                        can_crud=False,
                        created_at=now_utc(),
                        updated_at=now_utc(),
                    )
                )
                db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    init_db()


def user_to_dict(user: User) -> dict:
    return {
        "id": int(user.id),
        "name": user.name or "",
        "email": user.email or "",
        "phone": user.phone,
        "role": user.role or "employee",
        "is_active": bool(user.is_active),
        "can_crud": bool(user.can_crud),
        "created_at": user.created_at or now_utc(),
    }


def normalize_role(role: str) -> str:
    clean_role = (role or "employee").strip().lower()
    if clean_role not in {"admin", "employee"}:
        raise HTTPException(status_code=400, detail="Role must be admin or employee")
    return clean_role


def count_active_admins(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active == True).count()  # noqa: E712


def build_user_updates(payload: UserUpdate, db: Session, user_id: int) -> dict:
    role = normalize_role(payload.role)
    email = str(payload.email).strip().lower()
    existing = db.query(User).filter(User.email == email, User.id != int(user_id)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    updates = {
        "name": payload.name.strip(),
        "email": email,
        "phone": payload.phone,
        "role": role,
        "is_active": bool(payload.is_active),
        "can_crud": True if role == "admin" else bool(payload.can_crud),
        "updated_at": now_utc(),
    }
    if payload.password and payload.password.strip():
        if len(payload.password.strip()) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        updates["password_hash"] = hash_password(payload.password.strip())
    return updates


def validate_file(file: UploadFile | None):
    if file is None:
        return
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type for {file.filename}. Allowed: jpg, jpeg, png, pdf",
        )


def save_upload(site_id: int, upload: UploadFile | None, label: str) -> str | None:
    if upload is None:
        return None
    validate_file(upload)
    ext = Path(upload.filename or "").suffix.lower()
    site_dir = UPLOAD_DIR / f"site_{site_id}"
    site_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{label}_{uuid4().hex}{ext}"
    path = site_dir / safe_name
    with path.open("wb") as buffer:
        buffer.write(upload.file.read())
    return f"site_{site_id}/{safe_name}"


def file_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"/uploads/{path}"


def validate_site_payload(
    height_ft: float,
    width_ft: float,
    side_type: str,
    towards_1: str | None,
    towards_2: str | None,
    agreement_start_date: date,
    agreement_end_date: date,
):
    if height_ft <= 0 or width_ft <= 0:
        raise HTTPException(status_code=400, detail="Height and width must be greater than zero")
    if side_type == "Single" and not towards_1:
        raise HTTPException(status_code=400, detail="Towards field is required for single side")
    if side_type == "Double" and (not towards_1 or not towards_2):
        raise HTTPException(status_code=400, detail="Both towards fields are required for double side")
    if agreement_end_date < agreement_start_date:
        raise HTTPException(status_code=400, detail="Agreement end date cannot be before start date")


def parse_remarks_json(remarks_json: str | dict | None) -> dict[str, str]:
    if not remarks_json:
        return {}
    if isinstance(remarks_json, dict):
        data = remarks_json
    else:
        try:
            data = json.loads(remarks_json)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value).strip() for key, value in data.items() if str(value).strip()}


def format_remarks_for_excel(remarks: dict | str | None) -> str:
    parsed = parse_remarks_json(remarks)
    return " | ".join(f"{SECTION_REMARK_LABELS.get(key, key)}: {value}" for key, value in parsed.items())


def make_document_data(site: OOHSite | None) -> dict:
    return {
        "site_photo_uploaded": bool(site and site.site_photo_file),
        "landlord_photo_uploaded": bool(site and site.landlord_photo_file),
        "aadhaar_uploaded": bool(site and site.aadhaar_file),
        "pan_uploaded": bool(site and site.pan_file),
        "property_tax_uploaded": bool(site and site.property_tax_file),
        "passbook_uploaded": bool(site and site.passbook_file),
        "site_photo_file_url": file_url(site.site_photo_file if site else None),
        "landlord_photo_file_url": file_url(site.landlord_photo_file if site else None),
        "aadhaar_file_url": file_url(site.aadhaar_file if site else None),
        "pan_file_url": file_url(site.pan_file if site else None),
        "property_tax_file_url": file_url(site.property_tax_file if site else None),
        "passbook_file_url": file_url(site.passbook_file if site else None),
    }


def site_to_out(site: OOHSite, db: Session) -> SiteOut:
    creator = db.query(User).filter(User.id == site.created_by_user_id).first()
    return SiteOut(
        id=int(site.id),
        created_by_user_id=int(site.created_by_user_id),
        created_by_name=creator.name if creator else None,
        hoarding_location=site.hoarding_location,
        landlord_location=site.landlord_location,
        landlord_name=site.landlord_name,
        landlord_phone=site.landlord_phone,
        landlord_email=site.landlord_email,
        secondary_contact_name=site.secondary_contact_name,
        secondary_contact_phone=site.secondary_contact_phone,
        height_ft=float(site.height_ft),
        width_ft=float(site.width_ft),
        area_sqft=float(site.area_sqft),
        rental_type=site.rental_type,
        advance_amount=float(site.advance_amount or 0),
        light_type=site.light_type,
        side_type=site.side_type,
        towards_1=site.towards_1,
        towards_2=site.towards_2,
        latitude=site.latitude,
        longitude=site.longitude,
        agreement_tenure=site.agreement_tenure,
        agreement_start_date=site.agreement_start_date,
        agreement_end_date=site.agreement_end_date,
        remarks=parse_remarks_json(site.remarks),
        documents=make_document_data(site),
        created_at=site.created_at or now_utc(),
        updated_at=site.updated_at or now_utc(),
    )


def can_manage_site(current_user: User, site: OOHSite) -> bool:
    if current_user.role == "admin":
        return True
    return bool(current_user.can_crud) and int(site.created_by_user_id) == int(current_user.id)


def require_site_crud_permission(current_user: User, site: OOHSite):
    if not can_manage_site(current_user, site):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CRUD permission is blocked for this employee or this record.",
        )


def apply_document_uploads(
    site: OOHSite,
    site_photo_file: UploadFile | None = None,
    landlord_photo_file: UploadFile | None = None,
    aadhaar_file: UploadFile | None = None,
    pan_file: UploadFile | None = None,
    property_tax_file: UploadFile | None = None,
    passbook_file: UploadFile | None = None,
):
    uploaded_files = {
        "site_photo_file": save_upload(site.id, site_photo_file, "site_photo"),
        "landlord_photo_file": save_upload(site.id, landlord_photo_file, "landlord_photo"),
        "aadhaar_file": save_upload(site.id, aadhaar_file, "aadhaar"),
        "pan_file": save_upload(site.id, pan_file, "pan"),
        "property_tax_file": save_upload(site.id, property_tax_file, "property_tax"),
        "passbook_file": save_upload(site.id, passbook_file, "passbook"),
    }
    for field_name, stored_path in uploaded_files.items():
        if stored_path:
            setattr(site, field_name, stored_path)
    site.updated_at = now_utc()


def apply_site_fields(
    site: OOHSite,
    hoarding_location: str,
    landlord_location: str,
    landlord_name: str,
    landlord_phone: str,
    landlord_email: str | None,
    secondary_contact_name: str | None,
    secondary_contact_phone: str | None,
    height_ft: float,
    width_ft: float,
    rental_type: str,
    advance_amount: float,
    light_type: str,
    side_type: str,
    towards_1: str | None,
    towards_2: str | None,
    latitude: float | None,
    longitude: float | None,
    agreement_tenure: str,
    agreement_start_date: date,
    agreement_end_date: date,
    remarks_json: str | None,
):
    site.hoarding_location = hoarding_location.strip()
    site.landlord_location = landlord_location.strip()
    site.landlord_name = landlord_name.strip()
    site.landlord_phone = landlord_phone.strip()
    site.landlord_email = landlord_email.strip() if landlord_email else None
    site.secondary_contact_name = secondary_contact_name.strip() if secondary_contact_name else None
    site.secondary_contact_phone = secondary_contact_phone.strip() if secondary_contact_phone else None
    site.height_ft = float(height_ft)
    site.width_ft = float(width_ft)
    site.area_sqft = round(float(height_ft) * float(width_ft), 2)
    site.rental_type = rental_type
    site.advance_amount = float(advance_amount or 0)
    site.light_type = light_type
    site.side_type = side_type
    site.towards_1 = towards_1
    site.towards_2 = towards_2 if side_type == "Double" else None
    site.latitude = latitude
    site.longitude = longitude
    site.agreement_tenure = agreement_tenure
    site.agreement_start_date = agreement_start_date
    site.agreement_end_date = agreement_end_date
    site.remarks = parse_remarks_json(remarks_json)
    site.updated_at = now_utc()


@app.get("/api/health")
def health():
    ping_database()
    return {"status": "ok", "database": "neon-postgresql"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return TokenResponse(access_token=create_token(user), user=user_to_dict(user))


@app.get("/api/users/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return user_to_dict(current_user)


@app.post("/api/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    role = normalize_role(payload.role)
    existing = db.query(User).filter(User.email == str(payload.email).strip().lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    if len(payload.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = User(
        name=payload.name.strip(),
        email=str(payload.email).strip().lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password.strip()),
        role=role,
        is_active=True,
        can_crud=bool(payload.can_crud) if role == "employee" else True,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    db.refresh(user)
    return user_to_dict(user)


@app.get("/api/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [user_to_dict(user) for user in users]


@app.patch("/api/users/{user_id}/crud-permission", response_model=UserOut)
def update_user_crud_permission(
    user_id: int,
    payload: CrudPermissionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.can_crud = True if user.role == "admin" else bool(payload.can_crud)
    user.updated_at = now_utc()
    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@app.put("/api/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = build_user_updates(payload, db, int(user_id))

    if int(user_id) == int(current_user.id):
        if not updates.get("is_active", True):
            raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account")
        if updates.get("role") != "admin":
            raise HTTPException(status_code=400, detail="You cannot remove admin role from your own account")

    if user.role == "admin" and (updates.get("role") != "admin" or not updates.get("is_active", True)) and count_active_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="At least one active admin must remain")

    for key, value in updates.items():
        setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    db.refresh(user)
    return user_to_dict(user)


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if int(user_id) == int(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
    if user.role == "admin" and count_active_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="At least one active admin must remain")
    if db.query(OOHSite).filter(OOHSite.created_by_user_id == int(user_id)).count() > 0:
        user.is_active = False
        user.can_crud = False
        user.updated_at = now_utc()
        db.commit()
        return {"message": "User has existing OOH records, so the account was deactivated instead of permanently deleted."}
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@app.post("/api/sites", response_model=SiteOut)
def create_site(
    hoarding_location: str = Form(...),
    landlord_location: str = Form(...),
    landlord_name: str = Form(...),
    landlord_phone: str = Form(...),
    landlord_email: Optional[str] = Form(None),
    secondary_contact_name: Optional[str] = Form(None),
    secondary_contact_phone: Optional[str] = Form(None),
    height_ft: float = Form(...),
    width_ft: float = Form(...),
    rental_type: str = Form(...),
    advance_amount: float = Form(0),
    light_type: str = Form(...),
    side_type: str = Form(...),
    towards_1: Optional[str] = Form(None),
    towards_2: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    agreement_tenure: str = Form(...),
    agreement_start_date: date = Form(...),
    agreement_end_date: date = Form(...),
    remarks_json: Optional[str] = Form(None),
    site_photo_file: UploadFile | None = File(None),
    landlord_photo_file: UploadFile | None = File(None),
    aadhaar_file: UploadFile | None = File(None),
    pan_file: UploadFile | None = File(None),
    property_tax_file: UploadFile | None = File(None),
    passbook_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_site_payload(height_ft, width_ft, side_type, towards_1, towards_2, agreement_start_date, agreement_end_date)
    site = OOHSite(created_by_user_id=current_user.id)
    apply_site_fields(
        site,
        hoarding_location,
        landlord_location,
        landlord_name,
        landlord_phone,
        landlord_email,
        secondary_contact_name,
        secondary_contact_phone,
        height_ft,
        width_ft,
        rental_type,
        advance_amount,
        light_type,
        side_type,
        towards_1,
        towards_2,
        latitude,
        longitude,
        agreement_tenure,
        agreement_start_date,
        agreement_end_date,
        remarks_json,
    )
    site.created_at = now_utc()
    db.add(site)
    db.flush()
    apply_document_uploads(site, site_photo_file, landlord_photo_file, aadhaar_file, pan_file, property_tax_file, passbook_file)
    db.commit()
    db.refresh(site)
    return site_to_out(site, db)


@app.put("/api/sites/{site_id}", response_model=SiteOut)
def update_site(
    site_id: int,
    hoarding_location: str = Form(...),
    landlord_location: str = Form(...),
    landlord_name: str = Form(...),
    landlord_phone: str = Form(...),
    landlord_email: Optional[str] = Form(None),
    secondary_contact_name: Optional[str] = Form(None),
    secondary_contact_phone: Optional[str] = Form(None),
    height_ft: float = Form(...),
    width_ft: float = Form(...),
    rental_type: str = Form(...),
    advance_amount: float = Form(0),
    light_type: str = Form(...),
    side_type: str = Form(...),
    towards_1: Optional[str] = Form(None),
    towards_2: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    agreement_tenure: str = Form(...),
    agreement_start_date: date = Form(...),
    agreement_end_date: date = Form(...),
    remarks_json: Optional[str] = Form(None),
    site_photo_file: UploadFile | None = File(None),
    landlord_photo_file: UploadFile | None = File(None),
    aadhaar_file: UploadFile | None = File(None),
    pan_file: UploadFile | None = File(None),
    property_tax_file: UploadFile | None = File(None),
    passbook_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site = db.query(OOHSite).filter(OOHSite.id == int(site_id)).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_site_crud_permission(current_user, site)
    validate_site_payload(height_ft, width_ft, side_type, towards_1, towards_2, agreement_start_date, agreement_end_date)
    apply_site_fields(
        site,
        hoarding_location,
        landlord_location,
        landlord_name,
        landlord_phone,
        landlord_email,
        secondary_contact_name,
        secondary_contact_phone,
        height_ft,
        width_ft,
        rental_type,
        advance_amount,
        light_type,
        side_type,
        towards_1,
        towards_2,
        latitude,
        longitude,
        agreement_tenure,
        agreement_start_date,
        agreement_end_date,
        remarks_json,
    )
    apply_document_uploads(site, site_photo_file, landlord_photo_file, aadhaar_file, pan_file, property_tax_file, passbook_file)
    db.commit()
    db.refresh(site)
    return site_to_out(site, db)


@app.delete("/api/sites/{site_id}")
def delete_site(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(OOHSite).filter(OOHSite.id == int(site_id)).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_site_crud_permission(current_user, site)
    db.delete(site)
    db.commit()
    shutil.rmtree(UPLOAD_DIR / f"site_{site_id}", ignore_errors=True)
    return {"message": "OOH site deleted successfully"}


@app.get("/api/sites", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(OOHSite)
    if current_user.role != "admin":
        query = query.filter(OOHSite.created_by_user_id == int(current_user.id))
    sites = query.order_by(OOHSite.created_at.desc()).all()
    return [site_to_out(site, db) for site in sites]


@app.get("/api/sites/export/excel")
def export_sites_excel(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    sites = db.query(OOHSite).order_by(OOHSite.created_at.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "OOH Sites"
    headers = [
        "ID", "Entered By", "Hoarding Location", "Landlord Location", "Landlord Name",
        "Landlord Phone", "Landlord Email", "Secondary Name", "Secondary Phone",
        "Height ft", "Width ft", "Area sqft", "Rental Type", "Advance Rs",
        "Light", "Side", "Towards 1", "Towards 2", "Latitude", "Longitude",
        "Agreement Tenure", "Start Date", "End Date", "Site Photo", "Landlord Photo", "Aadhaar", "PAN", "Property Tax",
        "Passbook", "Remarks", "Created At"
    ]
    ws.append(headers)
    for site in sites:
        creator = db.query(User).filter(User.id == site.created_by_user_id).first()
        ws.append([
            site.id,
            creator.name if creator else "",
            site.hoarding_location,
            site.landlord_location,
            site.landlord_name,
            site.landlord_phone,
            site.landlord_email or "",
            site.secondary_contact_name or "",
            site.secondary_contact_phone or "",
            site.height_ft,
            site.width_ft,
            site.area_sqft,
            site.rental_type,
            site.advance_amount,
            site.light_type,
            site.side_type,
            site.towards_1 or "",
            site.towards_2 or "",
            site.latitude or "",
            site.longitude or "",
            site.agreement_tenure,
            site.agreement_start_date.isoformat() if site.agreement_start_date else "",
            site.agreement_end_date.isoformat() if site.agreement_end_date else "",
            "Uploaded" if site.site_photo_file else "Not Uploaded",
            "Uploaded" if site.landlord_photo_file else "Not Uploaded",
            "Uploaded" if site.aadhaar_file else "Not Uploaded",
            "Uploaded" if site.pan_file else "Not Uploaded",
            "Uploaded" if site.property_tax_file else "Not Uploaded",
            "Uploaded" if site.passbook_file else "Not Uploaded",
            format_remarks_for_excel(site.remarks),
            (site.created_at or now_utc()).strftime("%Y-%m-%d %H:%M"),
        ])
    for column_cells in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 45)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=adinn_ooh_sites.xlsx"},
    )


@app.get("/api/sites/{site_id}", response_model=SiteOut)
def get_site(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(OOHSite).filter(OOHSite.id == int(site_id)).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if current_user.role != "admin" and int(site.created_by_user_id) != int(current_user.id):
        raise HTTPException(status_code=403, detail="Not allowed")
    return site_to_out(site, db)
