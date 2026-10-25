"""
Module 5 — Lifecycle Orchestration & Renewal REST API Router
Exposes policy configuration, lineage graph management, and time-sensitive lifecycle evaluations.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path

from app.db.session import get_db
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ALL_ROLES,
)
from app.modules.auth.dependencies import (
    get_current_user,
    require_roles,
)
from app.modules.auth.models import User
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    LifecyclePolicyResponse,
    LineageCreateRequest,
    LineageResponse,
    LineageTreeResponse,
    LifecycleEvaluationRequest,
    LifecycleEvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
)
from app.modules.lifecycle.policy_service import (
    create_policy,
    approve_policy,
    activate_policy,
    get_policy_by_id,
    list_policies,
    get_or_create_default_demo_policy,
)
from app.modules.lifecycle.lineage_service import (
    create_renewal_lineage,
    get_lineage_by_id,
    get_lineage_tree,
)
from app.modules.lifecycle.evaluation_service import (
    evaluate_instrument_lifecycle,
    get_latest_evaluation_for_instrument,
    evaluate_batch_instruments,
)
from app.common.exceptions import AppException

router = APIRouter(prefix="/lifecycle", tags=["Module 5 — Lifecycle & Renewal"])
instruments_lifecycle_router = APIRouter(prefix="/instruments", tags=["Module 5 — Instrument Lifecycle & Lineage"])


# --- Policy Management Endpoints ------------------------------------------------

@router.post(
    "/policies",
    response_model=LifecyclePolicyResponse,
    summary="Create a new versioned lifecycle policy (Admin only)",
)
def create_lifecycle_policy_endpoint(
    payload: LifecyclePolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    return create_policy(
        db=db,
        payload=payload,
        created_by_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.get(
    "/policies",
    response_model=List[LifecyclePolicyResponse],
    summary="List versioned lifecycle policies",
)
def list_lifecycle_policies_endpoint(
    policy_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_demo: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ensure default demo policy is provisioned
    get_or_create_default_demo_policy(db)
    return list_policies(
        db=db,
        policy_code=policy_code,
        status=status,
        include_demo=include_demo,
    )


@router.get(
    "/policies/{policy_id}",
    response_model=LifecyclePolicyResponse,
    summary="Get lifecycle policy by ID",
)
def get_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        raise AppException(status_code=404, message=f"Policy '{policy_id}' not found", code="POLICY_NOT_FOUND")
    return policy


@router.post(
    "/policies/{policy_id}/approve",
    response_model=LifecyclePolicyResponse,
    summary="Approve a draft policy (Admin / Competent Authority)",
)
def approve_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_COMPETENT_AUTHORITY])),
):
    return approve_policy(
        db=db,
        policy_id=policy_id,
        approver_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.post(
    "/policies/{policy_id}/activate",
    response_model=LifecyclePolicyResponse,
    summary="Activate an approved policy (Admin only)",
)
def activate_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    return activate_policy(
        db=db,
        policy_id=policy_id,
        activator_user_id=current_user.id,
        actor_email=current_user.email,
    )


# --- Lineage Management Endpoints -----------------------------------------------

@router.post(
    "/lineage/renew",
    response_model=LineageResponse,
    summary="Create predecessor-successor renewal relationship link",
)
def create_renewal_lineage_endpoint(
    payload: LineageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    return create_renewal_lineage(
        db=db,
        payload=payload,
        created_by_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.get(
    "/lineage/{lineage_id}",
    response_model=LineageResponse,
    summary="Get lineage relationship details by ID",
)
def get_lineage_endpoint(
    lineage_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lineage = get_lineage_by_id(db, lineage_id)
    if not lineage:
        raise AppException(status_code=404, message=f"Lineage record '{lineage_id}' not found", code="LINEAGE_NOT_FOUND")
    return lineage


@instruments_lifecycle_router.get(
    "/{id}/lineage",
    response_model=LineageTreeResponse,
    summary="Get complete renewal lineage ancestry and successor chain for an instrument",
)
def get_instrument_lineage_tree_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_lineage_tree(db, instrument_id=id)


# --- Evaluation Endpoints -------------------------------------------------------

@router.post(
    "/evaluate",
    response_model=LifecycleEvaluationResponse,
    summary="Perform on-demand or demo lifecycle evaluation for an instrument",
)
def evaluate_lifecycle_endpoint(
    payload: LifecycleEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return evaluate_instrument_lifecycle(
        db=db,
        instrument_id=payload.instrument_id,
        policy_id=payload.policy_id,
        simulated_date=payload.simulated_date,
        force_record=payload.force_evaluation,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )


@instruments_lifecycle_router.get(
    "/{id}/lifecycle",
    response_model=Optional[LifecycleEvaluationResponse],
    summary="Get latest lifecycle evaluation snapshot for an instrument",
)
def get_instrument_latest_lifecycle_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = get_latest_evaluation_for_instrument(db, instrument_id=id)
    if not ev:
        # Trigger an initial on-demand evaluation if never evaluated
        ev = evaluate_instrument_lifecycle(
            db=db,
            instrument_id=id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
        )
    return ev


@router.post(
    "/batch-evaluate",
    response_model=BatchEvaluationResponse,
    summary="Trigger batch lifecycle evaluation across instruments",
)
def batch_evaluate_endpoint(
    payload: BatchEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    total, material, evals = evaluate_batch_instruments(
        db=db,
        instrument_ids=payload.instrument_ids,
        institution_id=payload.institution_id,
        simulated_date=payload.simulated_date,
        limit=payload.limit,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    return BatchEvaluationResponse(
        evaluated_count=total,
        material_transitions_count=material,
        evaluations=evals,
    )
