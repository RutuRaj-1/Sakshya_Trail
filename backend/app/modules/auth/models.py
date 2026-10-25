"""
Auth Module - SQLAlchemy User Model with RBAC and Institution Association
"""
import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from app.db.base import Base, TimestampMixin
from app.core.security import ALL_ROLES, ROLE_INSTITUTION_USER, INTERNAL_ROLES

if TYPE_CHECKING:
    from app.modules.institutions.models import Institution


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Normalized, lowercase unique email address
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Argon2 password hash; plaintext passwords must NEVER be saved
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Application role: SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, etc.
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=ROLE_INSTITUTION_USER)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Flag for provisioned accounts requiring immediate password rotation
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Institution association: Mandatory for INSTITUTION_USER, None for internal roles
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    institution: Mapped[Optional["Institution"]] = relationship("Institution", back_populates="users")

    @validates("email")
    def validate_email(self, key: str, address: str) -> str:
        if not address or "@" not in address:
            raise ValueError("Invalid email format")
        return address.lower().strip()

    @validates("role")
    def validate_role(self, key: str, role_name: str) -> str:
        if role_name not in ALL_ROLES:
            raise ValueError(f"Invalid application role '{role_name}'. Must be one of: {sorted(list(ALL_ROLES))}")
        return role_name
