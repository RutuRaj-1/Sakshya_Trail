"""
Auth Module - User Provisioning, Authentication, and Password Management Service
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.core.security import (
    hash_password,
    verify_password,
    ALL_ROLES,
    ROLE_INSTITUTION_USER,
    INTERNAL_ROLES,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import (
    AppException,
    NotFoundException,
    ConflictException,
    ForbiddenException,
)


def authenticate_user(
    db: Session,
    email: str,
    password: str,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> User:
    """
    Authenticates a user by email and password using Argon2 verification.
    Enforces active-account checks and logs auditable events.
    """
    normalized_email = email.lower().strip()
    user = db.scalar(select(User).where(User.email == normalized_email))

    if not user:
        log_audit_event(
            db=db,
            action="AUTH_LOGIN_FAILED",
            entity_type="user",
            entity_id=normalized_email,
            actor_email=normalized_email,
            outcome="FAILURE",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"reason": "User not found"},
        )
        raise AppException("Invalid credentials provided", status_code=401, code="INVALID_CREDENTIALS")

    if not user.is_active:
        log_audit_event(
            db=db,
            action="AUTH_LOGIN_REJECTED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            outcome="FAILURE",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"reason": "Account is inactive"},
        )
        raise AppException("Account is deactivated. Contact regulatory administrator.", status_code=403, code="INACTIVE_ACCOUNT")

    if not verify_password(password, user.password_hash):
        log_audit_event(
            db=db,
            action="AUTH_LOGIN_FAILED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            outcome="FAILURE",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"reason": "Password verification mismatch"},
        )
        raise AppException("Invalid credentials provided", status_code=401, code="INVALID_CREDENTIALS")

    # Successful login
    log_audit_event(
        db=db,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
    )
    return user


def provision_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
    role: str,
    institution_id: Optional[str] = None,
    must_change_password: bool = False,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> User:
    """
    Safely provisions a new user with role validation and institution scoping rules.
    """
    normalized_email = email.lower().strip()

    # 1. Validate application role
    if role not in ALL_ROLES:
        raise AppException(
            f"Invalid role '{role}'. Must be one of: {sorted(list(ALL_ROLES))}",
            status_code=400,
            code="INVALID_ROLE",
        )

    # 2. Enforce institution scoping rules
    if role == ROLE_INSTITUTION_USER:
        if not institution_id:
            raise AppException(
                "An institution user must be associated with exactly one valid institution.",
                status_code=400,
                code="INSTITUTION_ASSOCIATION_REQUIRED",
            )
        inst = db.scalar(select(Institution).where(Institution.id == institution_id))
        if not inst:
            raise NotFoundException("Specified institution does not exist.")
    else:
        # Internal roles must never have an institution association to prevent bypass
        if institution_id:
            raise AppException(
                f"Internal role '{role}' cannot be assigned an institution association.",
                status_code=400,
                code="INTERNAL_ROLE_CANNOT_HAVE_INSTITUTION",
            )

    # 3. Check for existing duplicate account
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise ConflictException(f"A user account with email '{normalized_email}' already exists.")

    # 4. Hash password with Argon2 (never plaintext)
    pw_hash = hash_password(password)

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        password_hash=pw_hash,
        role=role,
        is_active=True,
        must_change_password=must_change_password,
        institution_id=institution_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(
        db=db,
        action="USER_PROVISIONED",
        entity_type="user",
        entity_id=user.id,
        actor_email=actor_email or "SYSTEM_BOOTSTRAP",
        actor_role=actor_role or "SYSTEM",
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=ip_address,
        metadata={"provisioned_role": role, "institution_id": institution_id},
    )
    return user


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> User:
    """
    Changes a user's password after validating current credentials.
    Clears must_change_password flag and updates Argon2 hash.
    """
    if not verify_password(current_password, user.password_hash):
        log_audit_event(
            db=db,
            action="AUTH_PASSWORD_CHANGE_FAILED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=user.role,
            outcome="FAILURE",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"reason": "Incorrect current password"},
        )
        raise AppException("Current password is incorrect.", status_code=400, code="INVALID_CURRENT_PASSWORD")

    if len(new_password) < 8:
        raise AppException("New password must be at least 8 characters long.", status_code=400, code="PASSWORD_TOO_SHORT")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)

    log_audit_event(
        db=db,
        action="AUTH_PASSWORD_CHANGED",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
    )
    return user
