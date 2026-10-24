"""
Auth Module - API Routes
Provides role discovery, session identity, and permission scaffolding.
"""
from typing import List
from fastapi import APIRouter
from app.modules.auth.schemas import RoleInfo, UserRead
from app.core.security import (
    ROLE_AICTE_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_VIEWER,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Roles"])

ROLE_METADATA = [
    RoleInfo(
        name=ROLE_AICTE_ADMIN,
        display_name="AICTE Administrator",
        description="Full regulatory authority, release approvals, policy parameters and audit review.",
    ),
    RoleInfo(
        name=ROLE_SCRUTINY_OFFICER,
        display_name="Scrutiny Officer",
        description="Verification officer checking submitted FDR instruments, notices, and defect flags.",
    ),
    RoleInfo(
        name=ROLE_INSTITUTION_USER,
        display_name="Institution Representative",
        description="Institutional user submitting security deposits, renewal receipts, and release requests.",
    ),
    RoleInfo(
        name=ROLE_AUDITOR,
        display_name="Compliance Auditor",
        description="Independent scrutiny with read-only access to tamper-evident audit logs and history.",
    ),
    RoleInfo(
        name=ROLE_VIEWER,
        display_name="Read-Only Observer",
        description="Read-only visibility for reporting and regulatory oversight dashboards.",
    ),
]


@router.get("/roles", response_model=List[RoleInfo])
async def list_available_roles():
    """Returns available role categories according to AICTE Regulation governance."""
    return ROLE_METADATA


@router.get("/session/bootstrap")
async def get_bootstrap_context():
    """Initial session bootstrap information for client application hydration."""
    return {
        "status": "ready",
        "system": "FDR Sentinel Lifecycle Integrity",
        "auth_method": "role_based_session",
        "default_role": ROLE_AICTE_ADMIN,
        "available_roles": [r.name for r in ROLE_METADATA],
    }
