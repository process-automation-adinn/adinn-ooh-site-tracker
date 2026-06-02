from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: str = "employee"
    can_crud: bool = False


class UserUpdate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str | None = None
    role: str = "employee"
    is_active: bool = True
    can_crud: bool = False


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: str
    is_active: bool = True
    can_crud: bool = False
    created_at: datetime


class DocumentOut(BaseModel):
    site_photo_uploaded: bool = False
    landlord_photo_uploaded: bool = False
    aadhaar_uploaded: bool = False
    pan_uploaded: bool = False
    property_tax_uploaded: bool = False
    passbook_uploaded: bool = False
    site_photo_file_url: str | None = None
    landlord_photo_file_url: str | None = None
    aadhaar_file_url: str | None = None
    pan_file_url: str | None = None
    property_tax_file_url: str | None = None
    passbook_file_url: str | None = None


class CrudPermissionUpdate(BaseModel):
    can_crud: bool


class SiteOut(BaseModel):
    id: int
    created_by_user_id: int
    created_by_name: str | None = None
    hoarding_location: str
    landlord_location: str
    landlord_name: str
    landlord_phone: str
    landlord_email: str | None = None
    secondary_contact_name: str | None = None
    secondary_contact_phone: str | None = None
    height_ft: float
    width_ft: float
    area_sqft: float
    rental_type: str
    advance_amount: float
    light_type: str
    side_type: str
    towards_1: str | None = None
    towards_2: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    agreement_tenure: str
    agreement_start_date: date
    agreement_end_date: date
    remarks: dict[str, str] = Field(default_factory=dict)
    documents: DocumentOut
    created_at: datetime
    updated_at: datetime
