from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="employee", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_crud: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sites: Mapped[list["OOHSite"]] = relationship("OOHSite", back_populates="created_by")


class StoredFile(Base):
    __tablename__ = "stored_files"
    __table_args__ = (UniqueConstraint("site_id", "field_name", name="uq_stored_files_site_field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("ooh_sites.id"), index=True, nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)



class OOHSite(Base):
    __tablename__ = "ooh_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    hoarding_location: Mapped[str] = mapped_column(Text, nullable=False)
    landlord_location: Mapped[str] = mapped_column(Text, nullable=False)
    landlord_name: Mapped[str] = mapped_column(String(160), nullable=False)
    landlord_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    landlord_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    secondary_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    height_ft: Mapped[float] = mapped_column(Float, nullable=False)
    width_ft: Mapped[float] = mapped_column(Float, nullable=False)
    area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    size_boxes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    rental_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rent_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    advance_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    light_type: Mapped[str] = mapped_column(String(50), nullable=False)
    side_type: Mapped[str] = mapped_column(String(20), nullable=False)
    towards_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    towards_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interested_status: Mapped[str] = mapped_column(String(30), default="Not Selected", nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    agreement_tenure: Mapped[str] = mapped_column(String(30), nullable=False)
    agreement_start_date = mapped_column(Date, nullable=False)
    agreement_end_date = mapped_column(Date, nullable=False)
    agreement_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agreement_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remarks: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    site_photo_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    landlord_photo_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    aadhaar_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pan_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    property_tax_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    passbook_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by: Mapped[User] = relationship("User", back_populates="sites")
