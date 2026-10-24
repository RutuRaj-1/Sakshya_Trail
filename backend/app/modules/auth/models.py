"""
Auth Module - SQLAlchemy User Models
"""
import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="institution_user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    institution_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
