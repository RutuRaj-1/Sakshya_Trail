"""
Security, Password Hashing (Argon2), JWT Tokens, and Role Definitions
"""
from typing import Optional, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import jwt
from app.core.config import settings

# Initialize Argon2 password hasher with secure parameters
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# ------------------------------------------------------------------------------
# 7 Official Application Roles
# ------------------------------------------------------------------------------
ROLE_SYSTEM_ADMIN = "SYSTEM_ADMIN"
ROLE_SCRUTINY_OFFICER = "SCRUTINY_OFFICER"
ROLE_BRANCH_HEAD = "BRANCH_HEAD"
ROLE_COMPETENT_AUTHORITY = "COMPETENT_AUTHORITY"
ROLE_FINANCE_OFFICER = "FINANCE_OFFICER"
ROLE_INSTITUTION_USER = "INSTITUTION_USER"
ROLE_AUDITOR = "AUDITOR"

ALL_ROLES: Set[str] = {
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
}

INTERNAL_ROLES: Set[str] = {
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_AUDITOR,
}

# ------------------------------------------------------------------------------
# Password Hashing Functions
# ------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2 hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if hash needs rehashing due to parameter updates."""
    try:
        return _ph.check_needs_rehash(hashed_password)
    except Exception:
        return False


# ------------------------------------------------------------------------------
# JWT Token Generation & Verification
# ------------------------------------------------------------------------------
def create_access_token(
    user_id: str,
    email: str,
    role: str,
    institution_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed, short-lived JWT session token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email.lower().strip(),
        "role": role,
        "institution_id": institution_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "nbf": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "role"]},
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None


# ------------------------------------------------------------------------------
# Sanitization Utility (Ensures credentials never leak into logs or audit)
# ------------------------------------------------------------------------------
SENSITIVE_KEYS: Set[str] = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "old_password",
    "new_password",
    "confirm_password",
}


def sanitize_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively removes sensitive keys from dictionaries before auditing."""
    if not data:
        return {}
    sanitized: Dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        else:
            sanitized[k] = v
    return sanitized
