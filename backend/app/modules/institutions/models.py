"""
Institutions Module - Complete Foundational SQLAlchemy Institution Model
"""
import uuid
from typing import List, Optional
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Unique institution code (e.g. AICTE permanent ID "1-10924811")
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    legal_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Flexible bounded string for regulatory taxonomy
    institution_type: Mapped[str] = mapped_column(
        String(100),
        default="TECHNICAL_INSTITUTE",
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Contact details
    contact_name: Mapped[str] = mapped_column(String(255), default="Registrar / Nodal Officer", nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), default="+91-11-29581000", nullable=False)
    
    # Address details
    address_line1: Mapped[str] = mapped_column(String(255), default="Institutional Area", nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="New Delhi", nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), default="110070", nullable=False)
    
    assigned_office: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="institution", cascade="all, delete-orphan")

    # Compatibility properties for existing view layers
    @property
    def aicte_id(self) -> str:
        return self.code

    @property
    def name(self) -> str:
        return self.display_name or self.legal_name

    @property
    def category(self) -> str:
        return self.institution_type

    @property
    def status(self) -> str:
        return "ACTIVE" if self.is_active else "INACTIVE"
