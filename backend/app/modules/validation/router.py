"""
Module 3 — Validation API Router

Endpoints
---------
POST   /instruments/{instrument_id}/validate
       Trigger a full (or selective) validation run for an instrument.

GET    /instruments/{instrument_id}/findings
       List findings for an instrument (filterable by status, severity, category).

GET    /instruments/{instrument_id}/findings/{finding_id}
       Retrieve a specific finding.

POST   /instruments/{instrument_id}/findings/{finding_id}/dismiss
       Dismiss a finding (SCRUTINY_OFFICER / BRANCH_HEAD / SYSTEM_ADMIN).

GET    /validation/rules
       List all registered rules and their metadata.

GET    /validation/policy
       List active policy configurations (SYSTEM_ADMIN / SCRUTINY_OFFICER).

POST   /validation/policy
       Create or update a policy configuration value (SYSTEM_ADMIN only).

Authorization
-------------
* Triggering validation: SCRUTINY_OFFICER, BRANCH_HEAD, SYSTEM_ADMIN, COMPETENT_AUTHORITY.
* Viewing findings:      Any authenticated user (institution user sees only their instrument).
* Dismissing findings:   SCRUTINY_OFFICER, BRANCH_HEAD, SYSTEM_ADMIN.
* Policy management:     SYSTEM_ADMIN only (write); SCRUTINY_OFFICER / AUDITOR (read).
* NO endpoint in this router modifies Instrument.trust_level.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_active_user,
    require_roles,
    enforce_institution_scope,
)
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_AUDITOR,
    ROLE_INSTITUTION_USER,
)
from app.common.exceptions import NotFoundException, ForbiddenException
from app.common.schemas import StandardResponse

from app.modules.validation import engine as validation_engine
from app.modules.validation.finding_service import (
    get_findings_for_instrument,
    get_finding_by_id,
    dismiss_finding,
)
from app.modules.validation.policy_service import (
    list_policy_configs,
    set_policy_config,
)
from app.modules.validation.registry import rule_registry
from app.modules.validation.schemas import (
    RunValidationRequest,
    ValidationRunResponse,
    FindingResponse,
    FindingListResponse,
    DismissFindingRequest,
    RuleRegistryEntry,
    PolicyConfigResponse,
    PolicyConfigCreateRequest,
)

router = APIRouter(prefix="/validation", tags=["Validation — Module 3"])


# ---------------------------------------------------------------------------
# Helper: scope-check instrument access
# ---------------------------------------------------------------------------

def _get_instrument_or_404(db: Session, instrument_id: str) -> Instrument:
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{instrument_id}' not found.")
    return instrument


def _enforce_instrument_scope(current_user: User, instrument: Instrument) -> None:
    """INSTITUTION_USER may only access their own institution's instruments."""
    if current_user.role == ROLE_INSTITUTION_USER:
        if current_user.institution_id != instrument.institution_id:
            raise ForbiddenException(
                "You are not authorized to access findings for another institution's instrument."
            )


# ---------------------------------------------------------------------------
# 1. Trigger validation run
# ---------------------------------------------------------------------------

@router.post(
    "/instruments/{instrument_id}/run",
    response_model=ValidationRunResponse,
    status_code=200,
    summary="Run validation rules for an instrument",
    description=(
        "Execute enabled validation rules against the specified instrument. "
        "Returns structured rule outcomes and finding summary. "
        "Does NOT modify the instrument's trust level."
    ),
)
def run_validation_for_instrument(
    instrument_id: str,
    payload: RunValidationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY
        )
    ),
):
    instrument = _get_instrument_or_404(db, instrument_id)
    result = validation_engine.run_validation(
        db=db,
        instrument_id=instrument.id,
        triggered_by_user_id=current_user.id,
        rule_ids=payload.rule_ids,
    )
    return ValidationRunResponse(**result)


# ---------------------------------------------------------------------------
# 2. List findings for an instrument
# ---------------------------------------------------------------------------

@router.get(
    "/instruments/{instrument_id}/findings",
    response_model=FindingListResponse,
    summary="List validation findings for an instrument",
)
def list_findings(
    instrument_id: str,
    status: Optional[str] = Query(None, description="Filter by finding status (OPEN, IN_REVIEW, etc.)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)"),
    category: Optional[str] = Query(None, description="Filter by finding category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    instrument = _get_instrument_or_404(db, instrument_id)
    _enforce_instrument_scope(current_user, instrument)

    status_filter = [status] if status else None
    findings = get_findings_for_instrument(
        db=db,
        instrument_id=instrument_id,
        status_filter=status_filter,
        severity_filter=severity,
        category_filter=category,
        skip=skip,
        limit=limit,
    )

    # Count total (without pagination)
    from sqlalchemy import select as sa_select, func
    from app.modules.validation.models import ValidationFinding
    count_stmt = sa_select(func.count(ValidationFinding.id)).where(
        ValidationFinding.instrument_id == instrument_id
    )
    if status_filter:
        count_stmt = count_stmt.where(ValidationFinding.status.in_(status_filter))
    if severity:
        count_stmt = count_stmt.where(ValidationFinding.severity == severity)
    if category:
        count_stmt = count_stmt.where(ValidationFinding.category == category)
    total = db.scalar(count_stmt) or 0

    return FindingListResponse(
        items=[FindingResponse.from_orm(f) for f in findings],
        total=total,
        skip=skip,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# 3. Get a specific finding
# ---------------------------------------------------------------------------

@router.get(
    "/instruments/{instrument_id}/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Get a specific validation finding",
)
def get_finding(
    instrument_id: str,
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    instrument = _get_instrument_or_404(db, instrument_id)
    _enforce_instrument_scope(current_user, instrument)

    finding = get_finding_by_id(db, finding_id, instrument_id=instrument_id)
    if not finding:
        raise NotFoundException(f"Finding '{finding_id}' not found for instrument '{instrument_id}'.")

    return FindingResponse.from_orm(finding)


# ---------------------------------------------------------------------------
# 4. Dismiss a finding
# ---------------------------------------------------------------------------

@router.post(
    "/instruments/{instrument_id}/findings/{finding_id}/dismiss",
    response_model=FindingResponse,
    summary="Dismiss a finding (human reviewer decision)",
    description=(
        "Mark a finding as DISMISSED with a mandatory reason. "
        "Only SCRUTINY_OFFICER, BRANCH_HEAD, and SYSTEM_ADMIN may dismiss findings. "
        "Dismissal does not delete the finding — it is preserved for audit."
    ),
)
def dismiss_finding_endpoint(
    instrument_id: str,
    finding_id: str,
    payload: DismissFindingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    ),
):
    instrument = _get_instrument_or_404(db, instrument_id)
    finding = get_finding_by_id(db, finding_id, instrument_id=instrument_id)
    if not finding:
        raise NotFoundException(f"Finding '{finding_id}' not found for instrument '{instrument_id}'.")

    updated = dismiss_finding(
        db=db,
        finding=finding,
        dismissed_by_user_id=current_user.id,
        reason=payload.reason,
    )
    return FindingResponse.from_orm(updated)


# ---------------------------------------------------------------------------
# 5. List all registered rules
# ---------------------------------------------------------------------------

@router.get(
    "/rules",
    response_model=List[RuleRegistryEntry],
    summary="List all registered validation rules",
)
def list_rules(
    current_user: User = Depends(get_current_active_user),
):
    return rule_registry.list_all()


# ---------------------------------------------------------------------------
# 6. List policy configurations (read)
# ---------------------------------------------------------------------------

@router.get(
    "/policy",
    response_model=List[PolicyConfigResponse],
    summary="List active policy configuration values",
)
def list_policy(
    institution_id: Optional[str] = Query(None, description="Filter by institution (None = global)"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_AUDITOR)
    ),
):
    configs = list_policy_configs(db=db, institution_id=institution_id, active_only=active_only)
    return [PolicyConfigResponse.model_validate(c) for c in configs]


# ---------------------------------------------------------------------------
# 7. Create / update a policy configuration (write — SYSTEM_ADMIN only)
# ---------------------------------------------------------------------------

@router.post(
    "/policy",
    response_model=PolicyConfigResponse,
    status_code=201,
    summary="Create or update a policy configuration value (SYSTEM_ADMIN only)",
    description=(
        "Inserts a new versioned policy record and deactivates the previous active record "
        "for the same key. Audited. Only SYSTEM_ADMIN is authorized."
    ),
)
def create_or_update_policy(
    payload: PolicyConfigCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
):
    cfg = set_policy_config(
        db=db,
        config_key=payload.config_key,
        config_value=payload.config_value,
        value_type=payload.value_type,
        display_name=payload.display_name,
        authorized_by_user_id=current_user.id,
        institution_id=payload.institution_id,
        description=payload.description,
        effective_from=payload.effective_from,
    )
    return PolicyConfigResponse.model_validate(cfg)
