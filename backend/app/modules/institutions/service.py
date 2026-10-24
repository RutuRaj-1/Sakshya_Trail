"""
Institutions Module - Business Logic Service Layer
Enforces RBAC, institution scoping, field-level access, and audit event logging.
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.modules.institutions.models import Institution
from app.modules.institutions.schemas import InstitutionCreate, InstitutionUpdate
from app.modules.auth.models import User
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ALL_ROLES,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    ConflictException,
)


# Explicitly allowed contact fields that an INSTITUTION_USER may update on their own institution
INSTITUTION_USER_PERMITTED_FIELDS = {
    "contact_name",
    "contact_email",
    "contact_phone",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "postal_code",
}


def list_institutions(
    db: Session,
    current_user: User,
    search: Optional[str] = None,
    state: Optional[str] = None,
    institution_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Institution], int]:
    """
    List institutions visible to the caller according to Module 1 scoping rules:
    - INSTITUTION_USER: Strictly scoped to their own institution (current_user.institution_id).
    - Internal roles: Access across all registered institutions (with future regional office scoping).
    """
    stmt = select(Institution)
    count_stmt = select(func.count(Institution.id))

    # 1. Enforce Institution User scoping
    if current_user.role == ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            return [], 0
        stmt = stmt.where(Institution.id == current_user.institution_id)
        count_stmt = count_stmt.where(Institution.id == current_user.institution_id)
    else:
        # Internal roles can filter by active status, state, and type
        if is_active is not None:
            stmt = stmt.where(Institution.is_active == is_active)
            count_stmt = count_stmt.where(Institution.is_active == is_active)

    if state:
        stmt = stmt.where(Institution.state.ilike(f"%{state.strip()}%"))
        count_stmt = count_stmt.where(Institution.state.ilike(f"%{state.strip()}%"))

    if institution_type:
        stmt = stmt.where(Institution.institution_type == institution_type)
        count_stmt = count_stmt.where(Institution.institution_type == institution_type)

    if search:
        search_term = f"%{search.strip()}%"
        search_filter = or_(
            Institution.code.ilike(search_term),
            Institution.legal_name.ilike(search_term),
            Institution.display_name.ilike(search_term),
            Institution.city.ilike(search_term),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.order_by(Institution.created_at.desc()).offset(skip).limit(limit)).all()
    return items, total


def get_institution_by_id(
    db: Session,
    current_user: User,
    institution_id: str,
) -> Institution:
    """
    Retrieve one authorized institution record.
    - INSTITUTION_USER may only access their own institution.
    - Inactive institutions remain readable for historical records and audit traceability.
    """
    inst = db.scalar(select(Institution).where(Institution.id == institution_id))
    if not inst:
        raise NotFoundException(f"Institution with ID '{institution_id}' was not found.")

    if current_user.role == ROLE_INSTITUTION_USER:
        if current_user.institution_id != inst.id:
            raise ForbiddenException("You are not authorized to access this institution's records.")

    return inst


def create_institution(
    db: Session,
    current_user: User,
    payload: InstitutionCreate,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Institution:
    """
    Create a new registered institution.
    Strictly restricted to SYSTEM_ADMIN.
    Normalizes code and verifies code uniqueness.
    """
    if current_user.role != ROLE_SYSTEM_ADMIN:
        raise ForbiddenException("Only System Administrators are authorized to register new institutions.")

    code_raw = payload.code or getattr(payload, "aicte_id", None)
    if not code_raw or not code_raw.strip():
        raise AppException("Institution code is required and cannot be empty.", status_code=422, code="INVALID_INSTITUTION_CODE")

    normalized_code = code_raw.strip().upper()

    # Check for existing duplicate code
    existing = db.scalar(select(Institution).where(Institution.code == normalized_code))
    if existing:
        raise AppException(
            f"An institution with code '{normalized_code}' already exists.",
            status_code=409,
            code="DUPLICATE_INSTITUTION_CODE",
        )

    legal_name_raw = payload.legal_name or getattr(payload, "name", None)
    if not legal_name_raw or not legal_name_raw.strip():
        raise AppException("Legal name is required and cannot be empty after trimming.", status_code=422, code="INVALID_LEGAL_NAME")

    inst = Institution(
        code=normalized_code,
        legal_name=legal_name_raw.strip(),
        display_name=payload.display_name.strip() if payload.display_name else None,
        institution_type=payload.institution_type or "TECHNICAL_INSTITUTE",
        contact_name=payload.contact_name.strip() if payload.contact_name else "Registrar / Nodal Officer",
        contact_email=payload.contact_email.strip().lower(),
        contact_phone=payload.contact_phone.strip() if payload.contact_phone else "+91-11-29581000",
        address_line1=payload.address_line1.strip() if payload.address_line1 else "Institutional Area",
        address_line2=payload.address_line2.strip() if payload.address_line2 else None,
        city=payload.city.strip() if payload.city else "New Delhi",
        state=payload.state.strip(),
        postal_code=payload.postal_code.strip() if payload.postal_code else "110001",
        assigned_office=payload.assigned_office.strip() if payload.assigned_office else None,
        is_active=payload.is_active,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    log_audit_event(
        db=db,
        action="INSTITUTION_CREATED",
        entity_type="institution",
        entity_id=inst.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
        metadata={
            "code": inst.code,
            "legal_name": inst.legal_name,
            "state": inst.state,
            "institution_type": inst.institution_type,
        },
    )
    return inst


def update_institution(
    db: Session,
    current_user: User,
    institution_id: str,
    payload: InstitutionUpdate,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Institution:
    """
    Update permitted fields of an institution.
    - SYSTEM_ADMIN: May update institutional, contact, and address fields.
    - INSTITUTION_USER: May ONLY update contact/address fields for their own institution.
      Attempts to modify code, legal_name, is_active, institution_type, or assigned_office
      are explicitly rejected with 403 Forbidden.
    - AUDITOR / OTHER INTERNAL ROLES: Read-only access; cannot modify records.
    """
    inst = db.scalar(select(Institution).where(Institution.id == institution_id))
    if not inst:
        raise NotFoundException(f"Institution with ID '{institution_id}' was not found.")

    update_data = payload.model_dump(exclude_unset=True)

    if current_user.role == ROLE_INSTITUTION_USER:
        if current_user.institution_id != inst.id:
            raise ForbiddenException("You are not authorized to update another institution's details.")

        # Check for disallowed field modifications
        disallowed_fields = set(update_data.keys()) - INSTITUTION_USER_PERMITTED_FIELDS
        if disallowed_fields:
            raise ForbiddenException(
                f"Institution users are not permitted to change administrative fields: {sorted(list(disallowed_fields))}. "
                "Only contact and address fields may be updated."
            )
    elif current_user.role == ROLE_SYSTEM_ADMIN:
        # System Admin may update institutional details
        if "code" in update_data and update_data["code"]:
            norm_code = update_data["code"].strip().upper()
            if norm_code != inst.code:
                existing = db.scalar(select(Institution).where(Institution.code == norm_code))
                if existing:
                    raise AppException(
                        f"An institution with code '{norm_code}' already exists.",
                        status_code=409,
                        code="DUPLICATE_INSTITUTION_CODE",
                    )
                inst.code = norm_code
    else:
        # All other internal roles (Scrutiny, Branch Head, Competent Authority, Finance, Auditor) are read-only
        raise ForbiddenException("Your role has read-only access to institution records and cannot modify details.")

    # Apply permitted fields
    changed_fields = {}
    for key, value in update_data.items():
        if key == "code":
            continue
        if hasattr(inst, key):
            old_val = getattr(inst, key)
            new_val = value.strip() if isinstance(value, str) else value
            if old_val != new_val:
                setattr(inst, key, new_val)
                changed_fields[key] = {"old": old_val, "new": new_val}

    db.commit()
    db.refresh(inst)

    if changed_fields:
        log_audit_event(
            db=db,
            action="INSTITUTION_UPDATED",
            entity_type="institution",
            entity_id=inst.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="SUCCESS",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"changed_fields": list(changed_fields.keys())},
        )

    return inst


def set_institution_status(
    db: Session,
    current_user: User,
    institution_id: str,
    is_active: bool,
    reason: Optional[str] = None,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Institution:
    """
    Controlled activation/deactivation of an institution.
    Strictly restricted to SYSTEM_ADMIN.
    Institutions are never physically deleted to maintain historical integrity.
    """
    if current_user.role != ROLE_SYSTEM_ADMIN:
        raise ForbiddenException("Only System Administrators are authorized to change institution status.")

    inst = db.scalar(select(Institution).where(Institution.id == institution_id))
    if not inst:
        raise NotFoundException(f"Institution with ID '{institution_id}' was not found.")

    if inst.is_active == is_active:
        return inst

    inst.is_active = is_active
    db.commit()
    db.refresh(inst)

    action = "INSTITUTION_ACTIVATED" if is_active else "INSTITUTION_DEACTIVATED"
    log_audit_event(
        db=db,
        action=action,
        entity_type="institution",
        entity_id=inst.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
        metadata={
            "is_active": is_active,
            "reason": reason or "Administrative status update",
            "institution_code": inst.code,
        },
    )
    return inst
