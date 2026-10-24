"""
Auth Module - API Endpoints for Login, Logout, Session, Password Rotation, Roles, and User Administration
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Response, Request, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
)
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    ChangePasswordRequest,
    UserRead,
    UserProvisionRequest,
    UserUpdate,
    UserStatusUpdate,
    UserResetPasswordRequest,
    UserResetPasswordResponse,
    UserListResponse,
    RoleInfo,
)
from app.modules.auth.service import (
    authenticate_user,
    change_user_password,
    provision_user,
    list_users,
    get_user_by_id,
    update_user_profile,
    set_user_status,
    admin_reset_user_password,
)
from app.modules.auth.dependencies import (
    get_current_active_user,
    require_roles,
    verify_csrf_origin,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import ForbiddenException

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

ROLE_METADATA: List[RoleInfo] = [
    RoleInfo(
        name=ROLE_SYSTEM_ADMIN,
        display_name="System Administrator",
        description="Full technical administration, user provisioning, audit inspection, and system configuration.",
        is_internal=True,
        requires_institution=False,
    ),
    RoleInfo(
        name=ROLE_SCRUTINY_OFFICER,
        display_name="Scrutiny Officer",
        description="First-line regulatory reviewer verifying uploaded FDR instruments, dates, amounts, and lien markings.",
        is_internal=True,
        requires_institution=False,
    ),
    RoleInfo(
        name=ROLE_BRANCH_HEAD,
        display_name="Branch Head",
        description="Regional AICTE office head overseeing scrutiny queues, deficiency notices, and renewals.",
        is_internal=True,
        requires_institution=False,
    ),
    RoleInfo(
        name=ROLE_COMPETENT_AUTHORITY,
        display_name="Competent Authority",
        description="Statutory approval official with exclusive authority to grant final security deposit release decisions.",
        is_internal=True,
        requires_institution=False,
    ),
    RoleInfo(
        name=ROLE_FINANCE_OFFICER,
        display_name="Finance Officer",
        description="Financial verification officer reviewing bank guarantees, encashment directives, and account reconciliation.",
        is_internal=True,
        requires_institution=False,
    ),
    RoleInfo(
        name=ROLE_INSTITUTION_USER,
        display_name="Institution Representative",
        description="Authorized institutional nodal officer submitting FDR certificates, renewal receipts, and release applications.",
        is_internal=False,
        requires_institution=True,
    ),
    RoleInfo(
        name=ROLE_AUDITOR,
        display_name="Compliance Auditor",
        description="Independent oversight auditor with strictly read-only inspection access across records and audit trails.",
        is_internal=True,
        requires_institution=False,
    ),
]


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticates user, creates signed session, and sets secure HttpOnly cookie.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    user = authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
        request_ip=client_ip,
        request_id=request_id,
    )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return LoginResponse(
        success=True,
        message="Authentication successful",
        user=UserRead.model_validate(user),
        access_token=token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Clears the HttpOnly session cookie and logs audit event.
    """
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
    )

    if current_user:
        log_audit_event(
            db=db,
            action="AUTH_LOGOUT",
            entity_type="user",
            entity_id=current_user.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="SUCCESS",
            ip_address=request.client.host if request.client else None,
        )

    return {"success": True, "message": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns server-verified identity of currently authenticated user.
    """
    return current_user


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Rotates user password after verifying current credentials.
    Clears must_change_password flag upon successful rotation.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    change_user_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request_ip=client_ip,
        request_id=request_id,
    )
    return {"success": True, "message": "Password changed successfully"}


@router.get("/roles", response_model=List[RoleInfo])
async def list_roles():
    """Returns official AICTE Regulation Bureau role definitions."""
    return ROLE_METADATA


# ==============================================================================
# USER ADMINISTRATION ENDPOINTS (SYSTEM_ADMIN ONLY)
# ==============================================================================

@router.get("/users", response_model=UserListResponse)
def get_users_list(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    institution_id: Optional[str] = Query(None, description="Filter by institution association"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    List user accounts with pagination, search, and role filtering.
    Restricted to SYSTEM_ADMIN.
    """
    items, total = list_users(
        db=db,
        search=search,
        role=role,
        is_active=is_active,
        institution_id=institution_id,
        skip=skip,
        limit=limit,
    )
    return UserListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=UserRead)
def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve one user profile.
    Authorized for SYSTEM_ADMIN or the individual user themselves.
    """
    if current_user.role != ROLE_SYSTEM_ADMIN and current_user.id != user_id:
        raise ForbiddenException("You are not authorized to view another user's profile.")
    return get_user_by_id(db, user_id)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def provision_new_user(
    payload: UserProvisionRequest,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Authorized endpoint for SYSTEM_ADMIN to provision new application accounts.
    Enforces role allow-list and institution scoping requirements.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    user = provision_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        institution_id=payload.institution_id,
        must_change_password=payload.must_change_password,
        actor_email=current_admin.email,
        actor_role=current_admin.role,
        request_id=request_id,
        ip_address=client_ip,
    )
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Update permitted user profile fields (full name, role, institution association).
    Restricted to SYSTEM_ADMIN. Enforces last-administrator protection.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return update_user_profile(
        db=db,
        current_admin=current_admin,
        user_id=user_id,
        full_name=payload.full_name,
        role=payload.role,
        institution_id=payload.institution_id,
        request_ip=client_ip,
        request_id=request_id,
    )


@router.post("/users/{user_id}/status", response_model=UserRead)
def toggle_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Activate or deactivate a user account.
    Restricted to SYSTEM_ADMIN.
    Enforces last-administrator protection to prevent accidental lockout of all admins.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return set_user_status(
        db=db,
        current_admin=current_admin,
        user_id=user_id,
        is_active=payload.is_active,
        reason=payload.reason,
        request_ip=client_ip,
        request_id=request_id,
    )


@router.post("/users/{user_id}/reset-password", response_model=UserResetPasswordResponse)
def reset_user_password(
    user_id: str,
    payload: UserResetPasswordRequest,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Administrative password reset procedure.
    Sets temporary password and forces must_change_password on next login.
    Returns temporary password in response for the administrator to securely communicate.
    Never stores or logs raw password or secret in audit logs.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    temp_pwd = admin_reset_user_password(
        db=db,
        current_admin=current_admin,
        user_id=user_id,
        temporary_password=payload.temporary_password,
        request_ip=client_ip,
        request_id=request_id,
    )

    return UserResetPasswordResponse(
        success=True,
        message="Password reset successfully. The temporary password must be changed upon next user login.",
        temporary_password=temp_pwd,
        must_change_password=True,
    )
