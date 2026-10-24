"""
Instruments Module - SQLAlchemy Financial Instrument (FDR / Security Deposit) Model
"""
import uuid
from datetime import date
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class Instrument(Base, TimestampMixin):
    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id"), index=True, nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(200), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    
    # Status: DRAFT, SUBMITTED, UNDER_SCRUTINY, VERIFIED, MATURED, RENEWED, RELEASE_REQUESTED, RELEASED
    status: Mapped[str] = mapped_column(String(50), default="SUBMITTED", index=True, nullable=False)

    # Trust / Evidence Level (as defined in Context.md):
    # L1: Declared (by Institution)
    # L2: Document Consistent (OCR / Review match)
    # L3: Officer Verified
    # L4: Bank Confirmed
    verification_level: Mapped[str] = mapped_column(String(50), default="L1_DECLARED", nullable=False)
    
    joint_with_aicte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lien_marked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
