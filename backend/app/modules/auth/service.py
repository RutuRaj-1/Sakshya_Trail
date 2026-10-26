"""
Auth Module - User Provisioning, Authentication, and Administration Service
Enforces strict RBAC, institution scoping, last-admin protection, and audit logging.
"""
import secrets
import string
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.core.security import (
    hash_password,
    verify_password,
    ALL_ROLES,
    ROLE_SYSTEM_ADMIN,
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
    must_change_password: bool = True,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> User:
    """
    Safely provisions a new user with role validation and institution scoping rules.
    Only SYSTEM_ADMIN should invoke this in production.
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


def list_users(
    db: Session,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    institution_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[User], int]:
    """
    List user accounts with search and filtering for administrative oversight.
    """
    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)

    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)

    if institution_id:
        stmt = stmt.where(User.institution_id == institution_id)
        count_stmt = count_stmt.where(User.institution_id == institution_id)

    if search:
        search_term = f"%{search.strip()}%"
        search_filter = or_(
            User.email.ilike(search_term),
            User.full_name.ilike(search_term),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)).all()
    return items, total


def get_user_by_id(
    db: Session,
    user_id: str,
) -> User:
    """
    Retrieve one user account record by ID.
    """
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise NotFoundException(f"User account with ID '{user_id}' was not found.")
    return user


def update_user_profile(
    db: Session,
    current_admin: User,
    user_id: str,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    institution_id: Optional[str] = None,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> User:
    """
    Update permitted user profile fields:
    - Only SYSTEM_ADMIN can invoke this.
    - If changing role away from SYSTEM_ADMIN, last-admin protection is enforced.
    - Validates institution association rules for the new role.
    """
    user = get_user_by_id(db, user_id)
    changed_metadata = {}

    # 1. Role modification
    if role and role != user.role:
        if role not in ALL_ROLES:
            raise AppException(f"Invalid role '{role}'. Must be one of: {sorted(list(ALL_ROLES))}", status_code=400, code="INVALID_ROLE")

        # Check last active system administrator protection
        if user.role == ROLE_SYSTEM_ADMIN and user.is_active:
            active_admins = db.scalar(
                select(func.count(User.id)).where(User.role == ROLE_SYSTEM_ADMIN, User.is_active == True)
            ) or 0
            if active_admins <= 1:
                raise AppException(
                    "Cannot demote or change the role of the last active system administrator.",
                    status_code=400,
                    code="LAST_ADMIN_PROTECTED",
                )

        target_role = role
        target_inst_id = institution_id if institution_id is not None else user.institution_id

        # Validate institution requirement for the new role
        if target_role == ROLE_INSTITUTION_USER:
            if not target_inst_id:
                raise AppException(
                    "An institution user must be associated with an institution.",
                    status_code=400,
                    code="INSTITUTION_ASSOCIATION_REQUIRED",
                )
            inst = db.scalar(select(Institution).where(Institution.id == target_inst_id))
            if not inst:
                raise NotFoundException("Specified institution does not exist.")
            user.institution_id = target_inst_id
        else:
            # Internal roles cannot have institution associations
            user.institution_id = None

        changed_metadata["role"] = {"old": user.role, "new": target_role}
        user.role = target_role
    elif institution_id is not None and user.role == ROLE_INSTITUTION_USER:
        # Updating institution for an institution user
        inst = db.scalar(select(Institution).where(Institution.id == institution_id))
        if not inst:
            raise NotFoundException("Specified institution does not exist.")
        changed_metadata["institution_id"] = {"old": user.institution_id, "new": institution_id}
        user.institution_id = institution_id

    # 2. Full name
    if full_name and full_name.strip():
        new_name = full_name.strip()
        if new_name != user.full_name:
            changed_metadata["full_name"] = {"old": user.full_name, "new": new_name}
            user.full_name = new_name

    db.commit()
    db.refresh(user)

    if changed_metadata:
        log_audit_event(
            db=db,
            action="USER_PROFILE_UPDATED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=current_admin.id,
            actor_email=current_admin.email,
            actor_role=current_admin.role,
            outcome="SUCCESS",
            request_id=request_id,
            ip_address=request_ip,
            metadata=changed_metadata,
        )

        if "role" in changed_metadata:
            try:
                from app.modules.lifecycle.event_notification_service import emit_material_event
                emit_material_event(
                    db=db,
                    event_type="USER_ROLE_ASSIGNMENT_CHANGED",
                    entity_type="USER",
                    entity_id=user.id,
                    actor_user=current_admin,
                    resulting_state=user.role,
                    details={
                        "target_user_id": user.id,
                        "target_user_email": user.email,
                        "old_role": changed_metadata["role"]["old"],
                        "new_role": changed_metadata["role"]["new"],
                    },
                )
                db.commit()
            except Exception:
                pass

    return user


def set_user_status(
    db: Session,
    current_admin: User,
    user_id: str,
    is_active: bool,
    reason: Optional[str] = None,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> User:
    """
    Activate or deactivate a user account with last-admin protection.
    """
    user = get_user_by_id(db, user_id)

    if user.is_active == is_active:
        return user

    # Last active system administrator protection
    if not is_active and user.role == ROLE_SYSTEM_ADMIN:
        active_admins = db.scalar(
            select(func.count(User.id)).where(User.role == ROLE_SYSTEM_ADMIN, User.is_active == True)
        ) or 0
        if active_admins <= 1:
            raise AppException(
                "Cannot deactivate the last active system administrator.",
                status_code=400,
                code="LAST_ADMIN_PROTECTED",
            )

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    action = "USER_ACTIVATED" if is_active else "USER_DEACTIVATED"
    log_audit_event(
        db=db,
        action=action,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=current_admin.id,
        actor_email=current_admin.email,
        actor_role=current_admin.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
        metadata={
            "is_active": is_active,
            "target_email": user.email,
            "target_role": user.role,
            "reason": reason or "Administrative status change",
        },
    )
    return user


def admin_reset_user_password(
    db: Session,
    current_admin: User,
    user_id: str,
    temporary_password: Optional[str] = None,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> str:
    """
    Authorized administrative password reset procedure.
    Generates or assigns a temporary password and flags must_change_password = True.
    Never logs passwords or tokens in audit trails.
    """
    user = get_user_by_id(db, user_id)

    if not temporary_password:
        # Generate high-entropy temporary password: 12 chars (letters + digits + special)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_pwd = "".join(secrets.choice(alphabet) for _ in range(12))
    else:
        if len(temporary_password) < 8:
            raise AppException("Temporary password must be at least 8 characters long.", status_code=400, code="PASSWORD_TOO_SHORT")
        temp_pwd = temporary_password

    user.password_hash = hash_password(temp_pwd)
    user.must_change_password = True
    db.commit()
    db.refresh(user)

    # Audited without secret leakage
    log_audit_event(
        db=db,
        action="USER_PASSWORD_RESET_INITIATED",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=current_admin.id,
        actor_email=current_admin.email,
        actor_role=current_admin.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
        metadata={
            "target_email": user.email,
            "force_rotation": True,
            "procedure": "ADMIN_TEMPORARY_RESET",
        },
    )
    return temp_pwd


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
