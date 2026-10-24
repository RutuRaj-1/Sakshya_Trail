"""
Module 3 — Policy Configuration Service

Provides authorized, versioned access to validation policy configuration values.

Read path
---------
get_policy_for_instrument(db, instrument_id) → Dict[str, Any]
    Returns a merged dict of active policy values: institution-specific overrides
    take precedence over global values.

Write path (SYSTEM_ADMIN only — enforced by the API layer)
-------------------------------------------
set_policy_config(db, ...) → ValidationPolicyConfig
    Deactivates the previous active record for the same (institution_id, config_key)
    and inserts a new versioned record. Audited.

IMPORTANT: No user-facing numeric thresholds are hard-coded here.
"""
import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.modules.validation.models import ValidationPolicyConfig
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException


def get_active_policy_config(
    db: Session,
    config_key: str,
    institution_id: Optional[str] = None,
) -> Optional[ValidationPolicyConfig]:
    """
    Return the active policy config for a key, preferring institution-specific over global.
    """
    # 1. Try institution-specific first
    if institution_id:
        inst_cfg = db.scalar(
            select(ValidationPolicyConfig).where(
                and_(
                    ValidationPolicyConfig.config_key == config_key,
                    ValidationPolicyConfig.institution_id == institution_id,
                    ValidationPolicyConfig.is_active == True,  # noqa: E712
                )
            )
        )
        if inst_cfg:
            return inst_cfg

    # 2. Fall back to global (institution_id IS NULL)
    global_cfg = db.scalar(
        select(ValidationPolicyConfig).where(
            and_(
                ValidationPolicyConfig.config_key == config_key,
                ValidationPolicyConfig.institution_id.is_(None),
                ValidationPolicyConfig.is_active == True,  # noqa: E712
            )
        )
    )
    return global_cfg


def build_policy_context(
    db: Session,
    institution_id: str,
    instrument_id: Optional[str] = None,
    sibling_count: int = 0,
    sibling_ids: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Build the full policy dict that is passed into RuleContext.policy.

    Keys prefixed with '_' are engine-internal signals (not DB-sourced config values).
    """
    # Collect all active policy keys for this institution
    inst_configs = db.scalars(
        select(ValidationPolicyConfig).where(
            and_(
                ValidationPolicyConfig.institution_id == institution_id,
                ValidationPolicyConfig.is_active == True,  # noqa: E712
            )
        )
    ).all()

    global_configs = db.scalars(
        select(ValidationPolicyConfig).where(
            and_(
                ValidationPolicyConfig.institution_id.is_(None),
                ValidationPolicyConfig.is_active == True,  # noqa: E712
            )
        )
    ).all()

    # Global values first, then institution-specific overrides
    policy: Dict[str, Any] = {}
    version_refs = []

    for cfg in global_configs:
        policy[cfg.config_key] = cfg.parsed_value
        version_refs.append(f"{cfg.config_key}:v{cfg.policy_version}")

    for cfg in inst_configs:
        policy[cfg.config_key] = cfg.parsed_value
        version_refs.append(f"{cfg.config_key}[inst]:v{cfg.policy_version}")

    # Engine-internal signals for duplicate detection rule
    policy["_duplicate_sibling_count"] = sibling_count
    policy["_duplicate_sibling_ids"] = sibling_ids or []
    policy["_policy_version_ref"] = ",".join(version_refs) if version_refs else "no-policy"

    return policy


def set_policy_config(
    db: Session,
    config_key: str,
    config_value: str,
    value_type: str,
    display_name: str,
    authorized_by_user_id: str,
    institution_id: Optional[str] = None,
    description: Optional[str] = None,
    effective_from: Optional[str] = None,
) -> ValidationPolicyConfig:
    """
    Create or update a policy configuration value (authorized write path).

    Deactivates the existing active record for (config_key, institution_id) and
    creates a new versioned record. Audited via the audit service.

    Only SYSTEM_ADMIN should be permitted to call this — enforced by the API router.
    """
    # Validate value_type
    valid_types = {"decimal", "integer", "string", "json_list", "boolean"}
    if value_type not in valid_types:
        raise AppException(
            f"Invalid value_type '{value_type}'. Must be one of: {sorted(valid_types)}.",
            status_code=422,
            code="INVALID_POLICY_VALUE_TYPE",
        )

    # Validate the value is parseable for the given type
    _validate_policy_value(config_value, value_type)

    # Find current active record for versioning
    existing = db.scalar(
        select(ValidationPolicyConfig).where(
            and_(
                ValidationPolicyConfig.config_key == config_key,
                ValidationPolicyConfig.is_active == True,  # noqa: E712
                (
                    ValidationPolicyConfig.institution_id == institution_id
                    if institution_id
                    else ValidationPolicyConfig.institution_id.is_(None)
                ),
            )
        )
    )

    next_version = 1
    if existing:
        next_version = existing.policy_version + 1
        existing.is_active = False
        db.flush()

    new_cfg = ValidationPolicyConfig(
        config_key=config_key,
        institution_id=institution_id,
        config_value=config_value,
        value_type=value_type,
        display_name=display_name,
        description=description,
        policy_version=next_version,
        is_active=True,
        authorized_by_user_id=authorized_by_user_id,
        effective_from=effective_from,
    )
    db.add(new_cfg)
    db.commit()
    db.refresh(new_cfg)

    log_audit_event(
        db=db,
        action="POLICY_CONFIG_UPDATED",
        entity_type="validation_policy_config",
        entity_id=new_cfg.id,
        actor_user_id=authorized_by_user_id,
        outcome="SUCCESS",
        metadata={
            "config_key": config_key,
            "new_version": next_version,
            "institution_id": institution_id,
            "previous_version": next_version - 1 if existing else None,
        },
    )

    return new_cfg


def list_policy_configs(
    db: Session,
    institution_id: Optional[str] = None,
    active_only: bool = True,
) -> list:
    """List all policy configs, optionally filtered to active only and by institution."""
    stmt = select(ValidationPolicyConfig)
    if active_only:
        stmt = stmt.where(ValidationPolicyConfig.is_active == True)  # noqa: E712
    if institution_id is not None:
        stmt = stmt.where(ValidationPolicyConfig.institution_id == institution_id)
    stmt = stmt.order_by(ValidationPolicyConfig.config_key, ValidationPolicyConfig.policy_version.desc())
    return list(db.scalars(stmt).all())


def _validate_policy_value(value: str, value_type: str) -> None:
    """Raise AppException if value cannot be parsed as the specified type."""
    try:
        if value_type == "decimal":
            from decimal import Decimal
            Decimal(value)
        elif value_type == "integer":
            int(value)
        elif value_type == "boolean":
            if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError(f"Not a boolean: '{value}'")
        elif value_type == "json_list":
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError(f"Not a JSON array: '{value}'")
        # 'string' type: no validation needed
    except Exception as exc:
        raise AppException(
            f"Policy value '{value}' cannot be parsed as type '{value_type}': {exc}",
            status_code=422,
            code="INVALID_POLICY_VALUE",
        )
