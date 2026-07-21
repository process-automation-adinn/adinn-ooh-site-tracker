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
    can_crud: bool = True


class UserUpdate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str | None = None
    role: str = "employee"
    is_active: bool = True
    can_crud: bool = True


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: str
    is_active: bool = True
    can_crud: bool = True
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


class SizeBoxOut(BaseModel):
    label: str | None = None
    width_ft: float
    height_ft: float
    area_sqft: float


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
    size_boxes: list[SizeBoxOut] = Field(default_factory=list)
    rental_type: str
    rent_amount: float = 0
    advance_amount: float
    light_type: str
    side_type: str
    towards_1: str | None = None
    towards_2: str | None = None
    interested_status: str = "Interested"
    latitude: float | None = None
    longitude: float | None = None
    agreement_tenure: str
    agreement_start_date: date
    agreement_end_date: date
    agreement_created: bool = False
    agreement_created_at: datetime | None = None
    agreement_status: str = "Agreement Not Created"
    remarks: dict[str, str] = Field(default_factory=dict)
    documents: DocumentOut
    created_at: datetime
    updated_at: datetime
