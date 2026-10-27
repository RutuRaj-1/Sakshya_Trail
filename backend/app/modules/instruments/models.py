"""
Instruments Module - SQLAlchemy Financial Instrument (FDR / Security Deposit) Model
Represents statutory Fixed Deposit Receipts with strict decimal precision, parent institution
foreign key, separate administrative status, trust level (L0-L3), and derived maturity indicator.
"""
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Numeric, Date, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.institutions.models import Institution


class Instrument(Base, TimestampMixin):
    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Parent Institution Foreign Key
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Primary supported prototype type is FDR
    instrument_type: Mapped[str] = mapped_column(String(50), default="FDR", nullable=False)
    
    # Issuing Bank Details
    bank_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    branch: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Reference Number (Indexed, not globally unique to allow recording duplicates for regulatory review)
    reference_number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Precise Decimal monetary representation (never float)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    
    # Term Dates
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Lien and Joint Holder Information
    lien_holder: Mapped[Optional[str]] = mapped_column(
        String(255), default="AICTE Regulation Bureau", nullable=True
    )
    lien_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    joint_with_aicte: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lien_marked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Jurisdiction
    assigned_office: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Concept 1: Administrative Status (Registry initial states: DRAFT, REGISTERED)
    status: Mapped[str] = mapped_column(String(50), default="REGISTERED", index=True, nullable=False)

    # Concept 2: Trust Level (Evidence hierarchy: L0_DECLARED, L1_DOCUMENT_CONSISTENT, L2_OFFICER_VERIFIED, L3_BANK_CONFIRMED)
    trust_level: Mapped[str] = mapped_column(String(50), default="L0_DECLARED", index=True, nullable=False)

    # Prototype and Audit Metadata
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", back_populates="instruments")

    # Compatibility alias for earlier views
    @property
    def verification_level(self) -> str:
        return self.trust_level

    # Concept 3: Derived Read-Only Maturity Indicator (based on maturity date and authoritative business clock)
    @property
    def maturity_indicator(self) -> str:
        if self.maturity_date is None:
            return "UNKNOWN"
        from app.modules.lifecycle.clock import get_business_date
        today = get_business_date()
        if self.maturity_date < today:
            return "EXPIRED"
        elif self.maturity_date <= today + timedelta(days=90):
            return "EXPIRING_SOON"
        else:
            return "ACTIVE"
