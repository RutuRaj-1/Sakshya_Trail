"""
Module 3 — Validation API Router

Endpoints
---------
Standard versioned routes:
  POST   /api/v1/instruments/{instrument_id}/validation-runs
  GET    /api/v1/instruments/{instrument_id}/validation-runs
  GET    /api/v1/instruments/{instrument_id}/findings
  GET    /api/v1/findings/{finding_id}
  POST   /api/v1/findings/{finding_id}/re-evaluate
  POST   /api/v1/instruments/{instrument_id}/rules/{rule_id}/evaluate

Module-namespaced compatibility routes:
  POST   /api/v1/validation/instruments/{instrument_id}/run
  GET    /api/v1/validation/instruments/{instrument_id}/findings
  GET    /api/v1/validation/instruments/{instrument_id}/findings/{finding_id}
  POST   /api/v1/validation/instruments/{instrument_id}/findings/{finding_id}/dismiss
  GET    /api/v1/validation/rules
  GET    /api/v1/validation/policy
  POST   /api/v1/validation/policy

Authorization & Security
------------------------
* Validation runs: SCRUTINY_OFFICER, BRANCH_HEAD, SYSTEM_ADMIN, COMPETENT_AUTHORITY.
* Viewing findings / runs: Scoped to institution for INSTITUTION_USER; cross-institution denied.
* Dismissing findings: SCRUTINY_OFFICER, BRANCH_HEAD, SYSTEM_ADMIN.
* Single-rule evaluate: Strictly checks server-side allow-list; no arbitrary code execution.
* Direct updates to rule results, severity, evidence, or trust state from client payloads are rejected.
* Safe parameterized queries only.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, asc

from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_active_user,
    require_roles,
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
from app.common.exceptions import NotFoundException, ForbiddenException, AppException
from app.modules.validation import engine as validation_engine
from app.modules.validation.enums import FindingCategory
from app.modules.validation.models import ValidationFinding, ValidationRun
from app.modules.validation.finding_service import (
    get_findings_for_instrument,
    get_finding_by_id,
    dismiss_finding,
    re_evaluate_finding,
    get_validation_runs_for_instrument,
)
from app.modules.validation.policy_service import (
    list_policy_configs,
    set_policy_config,
)
from app.modules.validation.registry import rule_registry
from app.modules.validation.schemas import (
    RunValidationRequest,
    ValidationRunResponse,
    ValidationRunSummaryResponse,
    ValidationRunListResponse,
    FindingResponse,
    FindingListResponse,
    DismissFindingRequest,
    RuleRegistryEntry,
    PolicyConfigResponse,
    PolicyConfigCreateRequest,
)

# 1. Namespaced router (prefix: /validation)
router = APIRouter(prefix="/validation", tags=["Validation — Module 3"])

# 2. Direct resource router (prefix: /) for /instruments/... and /findings/...
instruments_validation_router = APIRouter(tags=["Validation — Module 3"])

ALLOWED_FINDING_SORT_FIELDS = {
    "first_detected_at": ValidationFinding.first_detected_at,
    "last_evaluated_at": ValidationFinding.last_evaluated_at,
    "severity": ValidationFinding.severity,
    "status": ValidationFinding.status,
    "created_at": ValidationFinding.created_at,
}


# ---------------------------------------------------------------------------
# Scope Enforcement Helpers
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
                "You are not authorized to access findings or validation runs for another institution's instrument."
            )


def _validate_rule_ids_and_category(
    rule_ids: Optional[List[str]], category: Optional[str]
) -> None:
    """Validate rule_ids against server-side registry allow-list and category against enums."""
    if rule_ids:
        all_rule_ids = {r.rule_id for r in rule_registry.get_enabled_rules()}
        for r_id in rule_ids:
            if r_id not in all_rule_ids and not rule_registry.get(r_id):
                raise AppException(
                    f"Rule '{r_id}' is not registered in the system rule catalogue.",
                    status_code=422,
                    code="UNREGISTERED_RULE",
                )
    if category:
        valid_categories = {c.value for c in FindingCategory} | {c.name for c in FindingCategory}
        if category.strip().upper() not in valid_categories:
            raise AppException(
                f"Finding category '{category}' is invalid. Allowed: {sorted(list(valid_categories))}.",
                status_code=422,
                code="INVALID_CATEGORY",
            )


# ---------------------------------------------------------------------------
# Handler Implementations
# ---------------------------------------------------------------------------

def _execute_run(
    instrument_id: str,
    payload: RunValidationRequest,
    current_user: User,
    db: Session,
) -> ValidationRunResponse:
    instrument = _get_instrument_or_404(db, instrument_id)
    _validate_rule_ids_and_category(payload.rule_ids, payload.category)

    result = validation_engine.run_validation(
        db=db,
        instrument_id=instrument.id,
        triggered_by_user_id=current_user.id,
        rule_ids=payload.rule_ids,
        category=payload.category,
    )
    return ValidationRunResponse(**result)


def _list_instrument_runs(
    instrument_id: str,
    skip: int,
    limit: int,
    current_user: User,
    db: Session,
) -> ValidationRunListResponse:
    instrument = _get_instrument_or_404(db, instrument_id)
    _enforce_instrument_scope(current_user, instrument)

    runs, total = get_validation_runs_for_instrument(db, instrument_id, skip=skip, limit=limit)
    items: List[ValidationRunSummaryResponse] = []
    for r in runs:
        rules_list = [x.strip() for x in r.rules_evaluated_csv.split(",") if x.strip()] if r.rules_evaluated_csv else []
        items.append(
            ValidationRunSummaryResponse(
                id=r.id,
                instrument_id=r.instrument_id,
                triggered_by_user_id=r.triggered_by_user_id,
                run_at=r.run_at,
                rules_evaluated=rules_list,
                outcome_summary=r.outcome_summary,
                new_findings_count=r.new_findings_count,
                resolved_findings_count=r.resolved_findings_count,
                run_status=r.run_status,
                policy_version_ref=r.policy_version_ref,
            )
        )
    return ValidationRunListResponse(items=items, total=total, skip=skip, limit=limit)


def _list_instrument_findings(
    instrument_id: str,
    status: Optional[str],
    severity: Optional[str],
    category: Optional[str],
    sort_by: str,
    sort_order: str,
    skip: int,
    limit: int,
    current_user: User,
    db: Session,
) -> FindingListResponse:
    instrument = _get_instrument_or_404(db, instrument_id)
    _enforce_instrument_scope(current_user, instrument)

    if sort_by not in ALLOWED_FINDING_SORT_FIELDS:
        raise AppException(
            f"Invalid sort_by field '{sort_by}'. Allowed: {sorted(list(ALLOWED_FINDING_SORT_FIELDS.keys()))}.",
            status_code=422,
            code="INVALID_SORT_FIELD",
        )

    stmt = select(ValidationFinding).where(ValidationFinding.instrument_id == instrument_id)
    count_stmt = select(func.count(ValidationFinding.id)).where(ValidationFinding.instrument_id == instrument_id)

    if status:
        stmt = stmt.where(ValidationFinding.status == status)
        count_stmt = count_stmt.where(ValidationFinding.status == status)
    if severity:
        stmt = stmt.where(ValidationFinding.severity == severity)
        count_stmt = count_stmt.where(ValidationFinding.severity == severity)
    if category:
        stmt = stmt.where(ValidationFinding.category == category)
        count_stmt = count_stmt.where(ValidationFinding.category == category)

    sort_col = ALLOWED_FINDING_SORT_FIELDS[sort_by]
    stmt = stmt.order_by(asc(sort_col) if sort_order.lower() == "asc" else desc(sort_col))
    stmt = stmt.offset(skip).limit(limit)

    findings = list(db.scalars(stmt).all())
    total = db.scalar(count_stmt) or 0

    return FindingListResponse(
        items=[FindingResponse.from_orm(f) for f in findings],
        total=total,
        skip=skip,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Direct Resource Endpoints (Prompt 2 API Specification)
# ---------------------------------------------------------------------------

@instruments_validation_router.post(
    "/instruments/{instrument_id}/validation-runs",
    response_model=ValidationRunResponse,
    status_code=200,
    summary="Execute validation run for an instrument",
)
def create_validation_run_direct(
    instrument_id: str,
    payload: RunValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY
        )
    ),
):
    return _execute_run(instrument_id, payload, current_user, db)


@instruments_validation_router.get(
    "/instruments/{instrument_id}/validation-runs",
    response_model=ValidationRunListResponse,
    summary="List validation run history for an instrument",
)
def list_validation_runs_direct(
    instrument_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _list_instrument_runs(instrument_id, skip, limit, current_user, db)


@instruments_validation_router.get(
    "/instruments/{instrument_id}/findings",
    response_model=FindingListResponse,
    summary="List validation findings for an instrument",
)
def list_findings_direct(
    instrument_id: str,
    status: Optional[str] = Query(None, description="Filter by status (OPEN, IN_REVIEW, RESOLVED, DISMISSED, SUPERSEDED)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by finding category"),
    sort_by: str = Query("first_detected_at", description="Sort field: first_detected_at, last_evaluated_at, severity, status, created_at"),
    sort_order: str = Query("desc", description="asc or desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _list_instrument_findings(
        instrument_id, status, severity, category, sort_by, sort_order, skip, limit, current_user, db
    )


@instruments_validation_router.get(
    "/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Retrieve finding by ID with tenant scope check",
)
def get_finding_by_id_direct(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    finding = db.scalar(select(ValidationFinding).where(ValidationFinding.id == finding_id))
    if not finding:
        raise NotFoundException(f"Finding '{finding_id}' not found.")
    instrument = _get_instrument_or_404(db, finding.instrument_id)
    _enforce_instrument_scope(current_user, instrument)
    return FindingResponse.from_orm(finding)


@instruments_validation_router.post(
    "/findings/{finding_id}/re-evaluate",
    response_model=FindingResponse,
    summary="Re-evaluate a specific finding",
)
def re_evaluate_finding_endpoint(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    ),
):
    finding = db.scalar(select(ValidationFinding).where(ValidationFinding.id == finding_id))
    if not finding:
        raise NotFoundException(f"Finding '{finding_id}' not found.")
    instrument = _get_instrument_or_404(db, finding.instrument_id)
    _enforce_instrument_scope(current_user, instrument)

    res = re_evaluate_finding(db, finding_id, actor_user_id=current_user.id)
    return FindingResponse.from_orm(res["finding"])


@instruments_validation_router.post(
    "/instruments/{instrument_id}/rules/{rule_id}/evaluate",
    response_model=ValidationRunResponse,
    summary="Evaluate a single allow-listed rule for testing/debugging",
)
def evaluate_single_rule_endpoint(
    instrument_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    ),
):
    instrument = _get_instrument_or_404(db, instrument_id)
    rule = rule_registry.get(rule_id)
    if not rule:
        raise AppException(
            f"Rule '{rule_id}' is not registered in the system rule catalogue.",
            status_code=404,
            code="RULE_NOT_FOUND",
        )

    result = validation_engine.run_validation(
        db=db,
        instrument_id=instrument.id,
        triggered_by_user_id=current_user.id,
        rule_ids=[rule_id],
    )
    return ValidationRunResponse(**result)


# ---------------------------------------------------------------------------
# Backward-Compatible Namespaced Endpoints (/validation/...)
# ---------------------------------------------------------------------------

@router.post(
    "/instruments/{instrument_id}/run",
    response_model=ValidationRunResponse,
    status_code=200,
    summary="Run validation rules for an instrument (compat route)",
)
def run_validation_compat(
    instrument_id: str,
    payload: RunValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY
        )
    ),
):
    return _execute_run(instrument_id, payload, current_user, db)


@router.get(
    "/instruments/{instrument_id}/findings",
    response_model=FindingListResponse,
    summary="List validation findings for an instrument (compat route)",
)
def list_findings_compat(
    instrument_id: str,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _list_instrument_findings(
        instrument_id, status, severity, category, "first_detected_at", "desc", skip, limit, current_user, db
    )


@router.get(
    "/instruments/{instrument_id}/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Get a specific validation finding (compat route)",
)
def get_finding_compat(
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


@router.post(
    "/instruments/{instrument_id}/findings/{finding_id}/dismiss",
    response_model=FindingResponse,
    summary="Dismiss a finding (human reviewer decision)",
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


@router.get(
    "/rules",
    response_model=List[RuleRegistryEntry],
    summary="List all registered validation rules",
)
def list_rules(
    current_user: User = Depends(get_current_active_user),
):
    return rule_registry.list_all()


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


@router.post(
    "/policy",
    response_model=PolicyConfigResponse,
    status_code=201,
    summary="Create or update a policy configuration value (SYSTEM_ADMIN only)",
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
