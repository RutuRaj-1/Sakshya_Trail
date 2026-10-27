"""
Centralized Authentication, RBAC, and Institution Scoping Dependencies
"""
from typing import Optional, List, Callable, Set
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.core.security import decode_access_token, ROLE_INSTITUTION_USER, ROLE_AUDITOR
from app.modules.auth.models import User
from app.common.exceptions import UnauthorizedException, ForbiddenException


def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extracts session token:
    1. Explicit Authorization Bearer header takes priority (API / direct client request).
    2. HttpOnly Cookie session fallback (browser frontend).
    """
    # 1. Authorization Header priority
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 2. HttpOnly Cookie fallback
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


def verify_csrf_origin(request: Request) -> None:
    """
    Validates Origin/Referer against allowed origins for state-changing operations
    to protect against CSRF attacks when using cookie authentication.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        is_dev = settings.ENVIRONMENT == "development" or settings.DEBUG

        # Allow requests if origin matches CORS whitelist or is local dev host
        if origin:
            if origin in settings.CORS_ORIGINS:
                return
            if is_dev and (origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")):
                return
            if any(origin.startswith(o) for o in settings.CORS_ORIGINS):
                return
            raise ForbiddenException("Cross-Origin request blocked by security policy")
        elif referer:
            if is_dev and (referer.startswith("http://localhost:") or referer.startswith("http://127.0.0.1:")):
                return
            if any(referer.startswith(o) for o in settings.CORS_ORIGINS):
                return
            raise ForbiddenException("Referer header origin mismatch")


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts token, decodes claims, and performs SERVER-SIDE user lookup
    so revoked or deactivated accounts immediately lose access.
    """
    token = extract_token_from_request(request)
    if not token:
        raise UnauthorizedException("Authentication session required")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedException("Invalid or expired session token")

    user_id = payload["sub"]

    # Fresh server-side lookup
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise UnauthorizedException("User session no longer exists")

    if not user.is_active:
        raise ForbiddenException("Account has been deactivated by administrator")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures user is active and has no pending restrictions."""
    if not current_user.is_active:
        raise ForbiddenException("User account is inactive")
    return current_user


def require_roles(*allowed_roles) -> Callable[[User], User]:
    """
    Centralized role-based access control dependency factory.
    Example: Depends(require_roles("SYSTEM_ADMIN", "SCRUTINY_OFFICER"))
    or: Depends(require_roles(["SYSTEM_ADMIN", "SCRUTINY_OFFICER"]))
    """
    roles = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple, set)):
            roles.extend(r)
        else:
            roles.append(r)
    role_set = set(roles)

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in role_set:
            raise ForbiddenException(
                f"Action forbidden for role '{current_user.role}'. Required: {sorted(list(role_set))}"
            )
        return current_user

    return role_checker


def enforce_institution_scope(user: User, target_institution_id: Optional[str]) -> None:
    """
    Enforces that INSTITUTION_USER can only access or modify records
    strictly matching their assigned institution.
    """
    if user.role == ROLE_INSTITUTION_USER:
        if not user.institution_id:
            raise ForbiddenException("Institution user is missing institution association")
        if target_institution_id and user.institution_id != target_institution_id:
            raise ForbiddenException("Access denied: You cannot view or modify records of another institution")


def require_read_only_or_permitted(user: User = Depends(get_current_active_user)) -> User:
    """
    Enforces that AUDITOR role has strictly read-only access.
    State-changing endpoints will block the auditor.
    """
    if user.role == ROLE_AUDITOR:
        raise ForbiddenException("Auditor role has strictly read-only inspection authority")
    return user
