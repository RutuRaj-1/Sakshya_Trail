"""
Instruments Module - Business Logic Service Layer
Handles validation, duplicate detection, ownership scoping, trust-level protection, and auditing.
"""
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, desc, asc

from app.modules.instruments.models import Instrument
from app.modules.institutions.models import Institution
from app.modules.auth.models import User
from app.modules.instruments.schemas import (
    InstrumentCreate,
    InstrumentUpdate,
    DuplicateWarningMatch,
    InstrumentResponse,
)
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_FINANCE_OFFICER,
    ROLE_COMPETENT_AUTHORITY,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    ConflictException,
)

ALLOW_LISTED_SORT_FIELDS = {
    "created_at": Instrument.created_at,
    "maturity_date": Instrument.maturity_date,
    "issue_date": Instrument.issue_date,
    "amount": Instrument.amount,
    "reference_number": Instrument.reference_number,
    "bank_name": Instrument.bank_name,
}

ALLOWED_REGISTRY_STATUSES = {"DRAFT", "REGISTERED", "SUBMITTED", "RETURNED_FOR_CORRECTION"}
ALLOWED_TRUST_LEVELS = {"L0_DECLARED", "L1_DOCUMENT_CONSISTENT", "L2_OFFICER_VERIFIED", "L3_BANK_CONFIRMED"}


def check_duplicate_reference(
    db: Session,
    bank_name: str,
    reference_number: str,
    exclude_id: Optional[str] = None,
) -> List[Instrument]:
    """
    Conservative duplicate detection:
    Compares normalized bank name and instrument reference case-insensitively.
    """
    norm_bank = bank_name.strip().lower()
    norm_ref = reference_number.strip().lower()

    stmt = select(Instrument).where(
        func.lower(func.trim(Instrument.bank_name)) == norm_bank,
        func.lower(func.trim(Instrument.reference_number)) == norm_ref,
    )
    if exclude_id:
        stmt = stmt.where(Instrument.id != exclude_id)

    return list(db.scalars(stmt).all())


def list_instruments(
    db: Session,
    current_user: User,
    search: Optional[str] = None,
    institution_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    trust_level: Optional[str] = None,
    maturity_start: Optional[date] = None,
    maturity_end: Optional[date] = None,
    maturity_indicator: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[InstrumentResponse], int]:
    """
    List instruments with search, multi-attribute filtering, stable allow-listed sorting,
    and strict institution scoping for INSTITUTION_USER.
    """
    stmt = select(Instrument).join(Institution, Instrument.institution_id == Institution.id)
    count_stmt = select(func.count(Instrument.id)).join(Institution, Instrument.institution_id == Institution.id)

    # 1. Enforce Institution User ownership scoping
    if current_user.role == ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            return [], 0
        stmt = stmt.where(Instrument.institution_id == current_user.institution_id)
        count_stmt = count_stmt.where(Instrument.institution_id == current_user.institution_id)
    elif institution_id:
        stmt = stmt.where(Instrument.institution_id == institution_id)
        count_stmt = count_stmt.where(Instrument.institution_id == institution_id)

    # 2. Authoritative business clock and lifecycle policy resolution
    from app.modules.lifecycle.clock import get_business_date
    from app.modules.lifecycle.policy_service import resolve_active_policy

    today = get_business_date()
    try:
        active_policy = resolve_active_policy(db, instrument_type="FDR")
        policy_intervals = active_policy.reminder_intervals_days if active_policy else [90]
        expiring_window_days = max(policy_intervals) if policy_intervals else 90
    except Exception:
        expiring_window_days = 90
    expiring_threshold = today + timedelta(days=expiring_window_days)

    if status_filter:
        if status_filter in ("EXPIRING_SOON",):
            stmt = stmt.where(Instrument.maturity_date >= today, Instrument.maturity_date <= expiring_threshold)
            count_stmt = count_stmt.where(Instrument.maturity_date >= today, Instrument.maturity_date <= expiring_threshold)
        elif status_filter in ("MATURED", "EXPIRED"):
            stmt = stmt.where(Instrument.maturity_date < today)
            count_stmt = count_stmt.where(Instrument.maturity_date < today)
        elif status_filter == "ACTIVE":
            stmt = stmt.where(Instrument.maturity_date > expiring_threshold)
            count_stmt = count_stmt.where(Instrument.maturity_date > expiring_threshold)
        elif status_filter in ("UNDER_SCRUTINY", "PENDING"):
            pending_statuses = ["DRAFT", "SUBMITTED", "UNDER_SCRUTINY", "UNDER_REVIEW", "RETURNED_FOR_CORRECTION"]
            stmt = stmt.where(Instrument.status.in_(pending_statuses))
            count_stmt = count_stmt.where(Instrument.status.in_(pending_statuses))
        else:
            stmt = stmt.where(Instrument.status == status_filter)
            count_stmt = count_stmt.where(Instrument.status == status_filter)

    if maturity_indicator:
        if maturity_indicator == "EXPIRING_SOON":
            stmt = stmt.where(Instrument.maturity_date >= today, Instrument.maturity_date <= expiring_threshold)
            count_stmt = count_stmt.where(Instrument.maturity_date >= today, Instrument.maturity_date <= expiring_threshold)
        elif maturity_indicator in ("MATURED", "EXPIRED"):
            stmt = stmt.where(Instrument.maturity_date < today)
            count_stmt = count_stmt.where(Instrument.maturity_date < today)
        elif maturity_indicator == "ACTIVE":
            stmt = stmt.where(Instrument.maturity_date > expiring_threshold)
            count_stmt = count_stmt.where(Instrument.maturity_date > expiring_threshold)

    if trust_level:
        stmt = stmt.where(Instrument.trust_level == trust_level)
        count_stmt = count_stmt.where(Instrument.trust_level == trust_level)

    if maturity_start:
        stmt = stmt.where(Instrument.maturity_date >= maturity_start)
        count_stmt = count_stmt.where(Instrument.maturity_date >= maturity_start)

    if maturity_end:
        stmt = stmt.where(Instrument.maturity_date <= maturity_end)
        count_stmt = count_stmt.where(Instrument.maturity_date <= maturity_end)

    if search:
        search_term = f"%{search.strip()}%"
        search_condition = or_(
            Instrument.reference_number.ilike(search_term),
            Instrument.bank_name.ilike(search_term),
            Institution.legal_name.ilike(search_term),
            Institution.code.ilike(search_term),
        )
        stmt = stmt.where(search_condition)
        count_stmt = count_stmt.where(search_condition)

    total = db.scalar(count_stmt) or 0

    # 3. Allow-listed sort
    sort_col = ALLOW_LISTED_SORT_FIELDS.get(sort_by, Instrument.created_at)
    order_func = desc if sort_order.lower() == "desc" else asc
    stmt = stmt.order_by(order_func(sort_col), desc(Instrument.id))

    instruments = db.scalars(stmt.offset(skip).limit(limit)).all()

    # Build response objects with joined institution metadata
    response_items = []
    for inst in instruments:
        parent_inst = db.scalar(select(Institution).where(Institution.id == inst.institution_id))
        resp = InstrumentResponse(
            id=inst.id,
            institution_id=inst.institution_id,
            institution_code=parent_inst.code if parent_inst else None,
            institution_name=parent_inst.legal_name if parent_inst else None,
            instrument_type=inst.instrument_type,
            bank_name=inst.bank_name,
            branch=inst.branch,
            reference_number=inst.reference_number,
            amount=inst.amount,
            currency=inst.currency,
            issue_date=inst.issue_date,
            maturity_date=inst.maturity_date,
            maturity_indicator=inst.maturity_indicator,
            lien_holder=inst.lien_holder,
            lien_details=inst.lien_details,
            joint_with_aicte=inst.joint_with_aicte,
            lien_marked=inst.lien_marked,
            assigned_office=inst.assigned_office,
            status=inst.status,
            trust_level=inst.trust_level,
            verification_level=inst.verification_level,
            is_synthetic=inst.is_synthetic,
            created_by_user_id=inst.created_by_user_id,
            updated_by_user_id=inst.updated_by_user_id,
            remarks=inst.remarks,
            created_at=inst.created_at,
            updated_at=inst.updated_at,
        )
        response_items.append(resp)

    return response_items, total


def get_instrument_by_id(
    db: Session,
    current_user: User,
    instrument_id: str,
) -> InstrumentResponse:
    """
    Retrieve one authorized instrument.
    Enforces scoping: INSTITUTION_USER may view only their own institution's instruments.
    """
    inst = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not inst:
        raise NotFoundException(f"Instrument with ID '{instrument_id}' was not found.")

    if current_user.role == ROLE_INSTITUTION_USER:
        if current_user.institution_id != inst.institution_id:
            raise ForbiddenException("You are not authorized to view an instrument belonging to another institution.")

    parent_inst = db.scalar(select(Institution).where(Institution.id == inst.institution_id))

    return InstrumentResponse(
        id=inst.id,
        institution_id=inst.institution_id,
        institution_code=parent_inst.code if parent_inst else None,
        institution_name=parent_inst.legal_name if parent_inst else None,
        instrument_type=inst.instrument_type,
        bank_name=inst.bank_name,
        branch=inst.branch,
        reference_number=inst.reference_number,
        amount=inst.amount,
        currency=inst.currency,
        issue_date=inst.issue_date,
        maturity_date=inst.maturity_date,
        maturity_indicator=inst.maturity_indicator,
        lien_holder=inst.lien_holder,
        lien_details=inst.lien_details,
        joint_with_aicte=inst.joint_with_aicte,
        lien_marked=inst.lien_marked,
        assigned_office=inst.assigned_office,
        status=inst.status,
        trust_level=inst.trust_level,
        verification_level=inst.verification_level,
        is_synthetic=inst.is_synthetic,
        created_by_user_id=inst.created_by_user_id,
        updated_by_user_id=inst.updated_by_user_id,
        remarks=inst.remarks,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


def create_instrument(
    db: Session,
    current_user: User,
    payload: InstrumentCreate,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> InstrumentResponse:
    """
    Registers a new security deposit instrument:
    - Scoping: INSTITUTION_USER may only register instruments for their own institution.
    - Institution validation: Rejects unknown or inactive institutions.
    - Amount validation: Must be Decimal > 0.
    - Date validation: maturity_date must be strictly later than issue_date.
    - Trust level: Must start at L0_DECLARED. Arbitrary escalation rejected.
    - Duplicate detection: Raises DUPLICATE_REFERENCE_WARNING if matching bank/reference exists
      unless confirm_duplicate=True is explicitly passed.
    """
    # 1. Authorization check
    if current_user.role == ROLE_INSTITUTION_USER:
        if payload.institution_id != current_user.institution_id:
            raise ForbiddenException("Institution users can only register instruments for their assigned institution.")
    elif current_user.role in (ROLE_AUDITOR, ROLE_FINANCE_OFFICER, ROLE_COMPETENT_AUTHORITY):
        raise ForbiddenException("Your role has read-only access and cannot register new instruments.")

    # 2. Institution existence and active status check
    institution = db.scalar(select(Institution).where(Institution.id == payload.institution_id))
    if not institution:
        raise NotFoundException(f"Institution with ID '{payload.institution_id}' does not exist.")
    if not institution.is_active:
        raise AppException(
            f"Institution '{institution.legal_name}' is currently deactivated. Registration of new instruments is blocked.",
            status_code=400,
            code="INACTIVE_INSTITUTION_REGISTRATION_BLOCKED",
        )

    # 3. Validation: Amount > 0
    if payload.amount <= Decimal("0"):
        raise AppException("Instrument amount must be greater than zero.", status_code=422, code="INVALID_AMOUNT")

    # 4. Validation: Dates
    if payload.maturity_date <= payload.issue_date:
        raise AppException("Maturity date must be strictly later than issue date.", status_code=422, code="INVALID_DATES")

    # 5. Normalization
    norm_bank = payload.bank_name.strip()
    norm_ref = payload.reference_number.strip().upper()

    # 6. Duplicate-Reference Warning Path
    matching_duplicates = check_duplicate_reference(db, norm_bank, norm_ref)
    if matching_duplicates and not payload.confirm_duplicate:
        # Build structured matches for warning response
        matches = []
        for m in matching_duplicates:
            m_parent = db.scalar(select(Institution).where(Institution.id == m.institution_id))
            matches.append({
                "id": m.id,
                "reference_number": m.reference_number,
                "bank_name": m.bank_name,
                "institution_id": m.institution_id,
                "institution_name": m_parent.legal_name if m_parent else None,
                "institution_code": m_parent.code if m_parent else None,
                "amount": str(m.amount),
                "issue_date": str(m.issue_date),
                "maturity_date": str(m.maturity_date),
                "status": m.status,
                "trust_level": m.trust_level,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            })

        raise AppException(
            message=f"Potential duplicate detected: An instrument with reference '{norm_ref}' at '{norm_bank}' is already registered.",
            status_code=409,
            code="DUPLICATE_REFERENCE_WARNING",
            details={
                "warning_message": "An instrument with the same reference number and issuing bank already exists in the registry. Review the existing record(s) below. To proceed with recording this instrument for regulatory inspection, confirm duplicate registration.",
                "matching_records": matches,
            },
        )

    # 7. Trust level must strictly start at L0_DECLARED
    trust_level = "L0_DECLARED"

    # 8. Status must be an initial registry status
    status = payload.status if payload.status in ALLOWED_REGISTRY_STATUSES else "REGISTERED"

    instrument = Instrument(
        institution_id=payload.institution_id,
        instrument_type=payload.instrument_type or "FDR",
        bank_name=norm_bank,
        branch=payload.branch.strip() if payload.branch else None,
        reference_number=norm_ref,
        amount=payload.amount,
        currency=payload.currency or "INR",
        issue_date=payload.issue_date,
        maturity_date=payload.maturity_date,
        lien_holder=payload.lien_holder.strip() if payload.lien_holder else "AICTE Regulation Bureau",
        lien_details=payload.lien_details.strip() if payload.lien_details else None,
        assigned_office=payload.assigned_office.strip() if payload.assigned_office else institution.assigned_office,
        status=status,
        trust_level=trust_level,
        joint_with_aicte=payload.joint_with_aicte,
        lien_marked=payload.lien_marked,
        remarks=payload.remarks.strip() if payload.remarks else None,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    # 9. Audit event
    log_audit_event(
        db=db,
        action="INSTRUMENT_CREATED",
        entity_type="instrument",
        entity_id=instrument.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        request_id=request_id,
        ip_address=request_ip,
        metadata={
            "reference_number": instrument.reference_number,
            "bank_name": instrument.bank_name,
            "institution_id": instrument.institution_id,
            "amount": str(instrument.amount),
            "trust_level": instrument.trust_level,
            "duplicate_warning_overridden": bool(matching_duplicates),
            "matching_record_ids": [m.id for m in matching_duplicates] if matching_duplicates else [],
        },
    )

    # Safe post-save evaluation trigger (does not fail creation if noncritical validation rule errors)
    try:
        from app.modules.validation.engine import trigger_post_save_validation
        trigger_post_save_validation(db=db, instrument_id=instrument.id, triggered_by_user_id=current_user.id)
    except Exception:
        pass

    # Module 4: Initialize baseline field provenance (L0_DECLARED)
    try:
        from app.modules.verification.provenance_service import initialize_instrument_provenance
        initialize_instrument_provenance(
            db=db,
            instrument=instrument,
            actor_user_id=current_user.id,
            source_type="INSTITUTION_ENTERED" if current_user.role == "INSTITUTION_USER" else "OFFICER_ENTERED",
        )
    except Exception:
        pass

    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="INSTRUMENT_SUBMITTED",
            entity_type="INSTRUMENT",
            entity_id=instrument.id,
            actor_user=current_user,
            instrument_id=instrument.id,
            institution_id=instrument.institution_id,
            resulting_state=instrument.status,
            details={
                "reference_number": instrument.reference_number,
                "bank_name": instrument.bank_name,
                "amount": str(instrument.amount),
            },
        )
        db.commit()
    except Exception:
        pass

    return InstrumentResponse(
        id=instrument.id,
        institution_id=instrument.institution_id,
        institution_code=institution.code,
        institution_name=institution.legal_name,
        instrument_type=instrument.instrument_type,
        bank_name=instrument.bank_name,
        branch=instrument.branch,
        reference_number=instrument.reference_number,
        amount=instrument.amount,
        currency=instrument.currency,
        issue_date=instrument.issue_date,
        maturity_date=instrument.maturity_date,
        maturity_indicator=instrument.maturity_indicator,
        lien_holder=instrument.lien_holder,
        lien_details=instrument.lien_details,
        joint_with_aicte=instrument.joint_with_aicte,
        lien_marked=instrument.lien_marked,
        assigned_office=instrument.assigned_office,
        status=instrument.status,
        trust_level=instrument.trust_level,
        verification_level=instrument.verification_level,
        is_synthetic=instrument.is_synthetic,
        created_by_user_id=instrument.created_by_user_id,
        updated_by_user_id=instrument.updated_by_user_id,
        remarks=instrument.remarks,
        created_at=instrument.created_at,
        updated_at=instrument.updated_at,
    )


def update_instrument(
    db: Session,
    current_user: User,
    instrument_id: str,
    payload: InstrumentUpdate,
    request_ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> InstrumentResponse:
    """
    Updates permitted registry fields of an instrument:
    - Rejects changing parent institution_id.
    - Rejects trust-level escalation (L0 -> L1/L2/L3) in Module 1.
    - Rejects unsupported administrative status transitions (e.g. to RELEASED / MATURED).
    - Checks duplicate warning if reference or bank name is modified.
    - Audited.
    """
    inst = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not inst:
        raise NotFoundException(f"Instrument with ID '{instrument_id}' was not found.")

    # 1. Scoping & Role checks
    if current_user.role == ROLE_INSTITUTION_USER:
        if current_user.institution_id != inst.institution_id:
            raise ForbiddenException("You cannot edit an instrument belonging to another institution.")
        # Institution users can only edit their own draft or registered instruments
        if inst.status not in ALLOWED_REGISTRY_STATUSES:
            raise ForbiddenException(f"Cannot edit instrument with workflow status '{inst.status}'.")
    elif current_user.role in (ROLE_AUDITOR, ROLE_FINANCE_OFFICER, ROLE_COMPETENT_AUTHORITY):
        raise ForbiddenException("Your role has read-only access to instrument records.")

    # 2. Rejection of trust-level escalation
    if payload.trust_level is not None and payload.trust_level != inst.trust_level:
        raise ForbiddenException(
            "Trust-level escalation is restricted to the verification workflow module. Ordinary registry updates cannot alter trust level."
        )

    # 3. Rejection of unsupported status transitions
    if payload.status is not None and payload.status != inst.status:
        if payload.status not in ALLOWED_REGISTRY_STATUSES:
            raise AppException(
                f"Unsupported registry status '{payload.status}'. Later lifecycle stages belong to the workflow module.",
                status_code=400,
                code="UNSUPPORTED_STATUS_TRANSITION",
            )

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("confirm_duplicate", None)
    update_data.pop("trust_level", None)

    # 4. Dates validation if dates provided
    new_issue = update_data.get("issue_date", inst.issue_date)
    new_maturity = update_data.get("maturity_date", inst.maturity_date)
    if new_maturity <= new_issue:
        raise AppException("Maturity date must be strictly later than issue date.", status_code=422, code="INVALID_DATES")

    # 5. Amount validation if amount provided
    if "amount" in update_data and update_data["amount"] <= Decimal("0"):
        raise AppException("Instrument amount must be greater than zero.", status_code=422, code="INVALID_AMOUNT")

    # 6. Duplicate check if bank or reference is modified
    target_bank = update_data.get("bank_name", inst.bank_name).strip()
    target_ref = update_data.get("reference_number", inst.reference_number).strip().upper()
    if target_bank.lower() != inst.bank_name.lower() or target_ref.lower() != inst.reference_number.lower():
        matching = check_duplicate_reference(db, target_bank, target_ref, exclude_id=inst.id)
        if matching and not payload.confirm_duplicate:
            matches = []
            for m in matching:
                matches.append({
                    "id": m.id,
                    "reference_number": m.reference_number,
                    "bank_name": m.bank_name,
                    "institution_id": m.institution_id,
                    "amount": str(m.amount),
                })
            raise AppException(
                message=f"Potential duplicate detected: An instrument with reference '{target_ref}' at '{target_bank}' already exists.",
                status_code=409,
                code="DUPLICATE_REFERENCE_WARNING",
                details={"matching_records": matches},
            )

    # Apply updates
    old_status = inst.status
    changed_fields = {}
    for key, value in update_data.items():
        if hasattr(inst, key):
            old_val = getattr(inst, key)
            if old_val != value:
                setattr(inst, key, value)
                changed_fields[key] = {"old": str(old_val), "new": str(value)}

    inst.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(inst)

    if changed_fields:
        log_audit_event(
            db=db,
            action="INSTRUMENT_UPDATED",
            entity_type="instrument",
            entity_id=inst.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="SUCCESS",
            request_id=request_id,
            ip_address=request_ip,
            metadata={"changed_fields": list(changed_fields.keys())},
        )

    # Safe post-save evaluation trigger on material update
    try:
        from app.modules.validation.engine import trigger_post_save_validation
        trigger_post_save_validation(db=db, instrument_id=inst.id, triggered_by_user_id=current_user.id)
    except Exception:
        pass

    # Module 4: Record provenance for updated fields
    try:
        from app.modules.verification.provenance_service import record_field_provenance
        from app.modules.verification.enums import TRACKED_FIELDS_SET
        for f_name, f_diff in changed_fields.items():
            if f_name in TRACKED_FIELDS_SET:
                record_field_provenance(
                    db=db,
                    instrument_id=inst.id,
                    field_name=f_name,
                    value=getattr(inst, f_name),
                    source_type="INSTITUTION_ENTERED" if current_user.role == "INSTITUTION_USER" else "OFFICER_ENTERED",
                    actor_user_id=current_user.id,
                    evidence_reference="Instrument field update",
                )
    except Exception:
        pass

    # Module 5: Emit material event if returned for correction
    if "status" in changed_fields and inst.status == "RETURNED_FOR_CORRECTION":
        try:
            from app.modules.lifecycle.event_notification_service import emit_material_event
            emit_material_event(
                db=db,
                event_type="SUBMISSION_RETURNED_FOR_CORRECTION",
                entity_type="INSTRUMENT",
                entity_id=inst.id,
                actor_user=current_user,
                instrument_id=inst.id,
                institution_id=inst.institution_id,
                resulting_state=inst.status,
                details={
                    "reference_number": inst.reference_number,
                    "reason": inst.remarks or "Corrections requested on submitted instrument.",
                },
            )
            db.commit()
        except Exception:
            pass
    elif old_status == "RETURNED_FOR_CORRECTION" and current_user.role == "INSTITUTION_USER":
        # Institution submitted correction response
        inst.status = "SUBMITTED"
        db.commit()
        db.refresh(inst)
        try:
            from app.modules.lifecycle.event_notification_service import emit_material_event
            emit_material_event(
                db=db,
                event_type="CORRECTION_RESPONSE_SUBMITTED",
                entity_type="INSTRUMENT",
                entity_id=inst.id,
                actor_user=current_user,
                instrument_id=inst.id,
                institution_id=inst.institution_id,
                resulting_state=inst.status,
                details={
                    "reference_number": inst.reference_number,
                    "changed_fields": list(changed_fields.keys()),
                },
            )
            db.commit()
        except Exception:
            pass

    parent_inst = db.scalar(select(Institution).where(Institution.id == inst.institution_id))

    return InstrumentResponse(
        id=inst.id,
        institution_id=inst.institution_id,
        institution_code=parent_inst.code if parent_inst else None,
        institution_name=parent_inst.legal_name if parent_inst else None,
        instrument_type=inst.instrument_type,
        bank_name=inst.bank_name,
        branch=inst.branch,
        reference_number=inst.reference_number,
        amount=inst.amount,
        currency=inst.currency,
        issue_date=inst.issue_date,
        maturity_date=inst.maturity_date,
        maturity_indicator=inst.maturity_indicator,
        lien_holder=inst.lien_holder,
        lien_details=inst.lien_details,
        joint_with_aicte=inst.joint_with_aicte,
        lien_marked=inst.lien_marked,
        assigned_office=inst.assigned_office,
        status=inst.status,
        trust_level=inst.trust_level,
        verification_level=inst.verification_level,
        is_synthetic=inst.is_synthetic,
        created_by_user_id=inst.created_by_user_id,
        updated_by_user_id=inst.updated_by_user_id,
        remarks=inst.remarks,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


def get_instruments_summary(db: Session, current_user: User) -> Dict[str, Any]:
    """
    Computes summary KPI metrics for FDR oversight, scoped by institution for INSTITUTION_USER.
    """
    today = date.today()
    in_90_days = today + timedelta(days=90)

    conditions = []
    if current_user.role == ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            return {
                "total_instruments": 0,
                "active_count": 0,
                "expiring_soon_count": 0,
                "under_scrutiny_count": 0,
                "released_count": 0,
                "total_deposit_value": Decimal("0.00"),
            }
        conditions.append(Instrument.institution_id == current_user.institution_id)

    total_count = db.scalar(select(func.count(Instrument.id)).where(*conditions)) or 0
    active_count = db.scalar(
        select(func.count(Instrument.id)).where(
            *conditions,
            Instrument.status.in_(["REGISTERED", "VERIFIED", "ACTIVE"]),
        )
    ) or 0
    expiring_soon = db.scalar(
        select(func.count(Instrument.id)).where(
            *conditions,
            Instrument.maturity_date >= today,
            Instrument.maturity_date <= in_90_days,
            Instrument.status != "RELEASED",
        )
    ) or 0
    scrutiny_count = db.scalar(
        select(func.count(Instrument.id)).where(
            *conditions,
            Instrument.status.in_(["DRAFT", "SUBMITTED", "UNDER_SCRUTINY"]),
        )
    ) or 0
    released_count = db.scalar(
        select(func.count(Instrument.id)).where(
            *conditions,
            Instrument.status == "RELEASED",
        )
    ) or 0
    total_val = db.scalar(
        select(func.coalesce(func.sum(Instrument.amount), Decimal("0.00"))).where(*conditions)
    ) or Decimal("0.00")

    return {
        "total_instruments": total_count,
        "active_count": active_count,
        "expiring_soon_count": expiring_soon,
        "under_scrutiny_count": scrutiny_count,
        "released_count": released_count,
        "total_deposit_value": Decimal(str(total_val)),
    }
