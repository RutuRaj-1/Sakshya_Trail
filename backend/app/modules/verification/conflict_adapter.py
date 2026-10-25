"""
Module 4 — Conflict Detection Adapter
Narrow interface between Module 4 (Trust) and Module 3 (Validation / Findings).

When an incoming verification response or accepted evidence differs from the
current instrument record, this adapter creates a discrepancy finding in Module 3
without coupling Module 4 to Module 3's internal implementation details.

Design contracts:
- Does NOT own the ValidationFinding table.
- Does NOT modify trust_level.
- Does NOT approve, reject, or resolve findings on behalf of Module 4.
- Reports any integration gap clearly rather than silently swallowing errors.
- Returns a minimal result so Module 4 can surface the conflict to officers.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.modules.validation.enums import (
    FindingCategory,
    FindingStatus,
    RuleOutcome,
    RuleSeverity,
    RuleType,
)
from app.modules.validation.models import ValidationFinding


@dataclass
class ConflictRecord:
    """Minimal result returned after a conflict is recorded."""
    finding_id: str
    field_name: str
    instrument_value: str
    conflicting_source_value: str
    source_type: str          # e.g. "BANK_RESPONSE", "MANUAL_EVIDENCE"
    source_reference: str     # e.g. verification response ID
    detected_at: datetime


def report_verification_conflict(
    db: Session,
    instrument_id: str,
    institution_id: str,
    field_name: str,
    instrument_value: str,
    conflicting_source_value: str,
    source_type: str,
    source_reference: str,
    verification_response_id: Optional[str] = None,
    document_id: Optional[str] = None,
    document_version_id: Optional[str] = None,
) -> ConflictRecord:
    """
    Record a conflict between the instrument's stored value and an incoming
    bank response or accepted evidence value.

    Behaviour:
    - Preserves BOTH the instrument value and the conflicting source value.
    - Creates a ValidationFinding with category CROSS_SOURCE_RECONCILIATION.
    - Does NOT overwrite any instrument field.
    - Does NOT set trust level.
    - Returns a ConflictRecord so callers can surface it to officers.

    If the ValidationFinding table is inaccessible (schema error, missing table,
    etc.), raises the original exception with a clear message reporting the gap
    rather than silently suppressing it.
    """
    now = datetime.now(timezone.utc)

    # Build a stable fingerprint for this conflict event
    fingerprint_input = json.dumps({
        "instrument_id": instrument_id,
        "field_name": field_name,
        "source_reference": source_reference,
    }, sort_keys=True)

    import hashlib
    fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()

    evidence_refs: List[str] = []
    if verification_response_id:
        evidence_refs.append(verification_response_id)
    if document_version_id:
        evidence_refs.append(document_version_id)

    finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=fingerprint,
        instrument_id=instrument_id,
        institution_id=institution_id,
        document_id=document_id,
        document_version_id=document_version_id,
        rule_id=f"TRUST_CONFLICT_{field_name.upper()}",
        rule_version="1.0",
        rule_type=RuleType.DETERMINISTIC.value,
        category=FindingCategory.CROSS_SOURCE_RECONCILIATION.value,
        severity=RuleSeverity.HIGH.value,
        status=FindingStatus.OPEN.value,
        title=(
            f"Conflict detected on field '{field_name}': "
            f"instrument value differs from {source_type} source"
        ),
        explanation=(
            f"The instrument records '{instrument_value}' for '{field_name}', but "
            f"the incoming {source_type} source (ref: {source_reference}) reports "
            f"'{conflicting_source_value}'. Both values are preserved. "
            "An authorized officer must review and resolve this discrepancy before "
            "trust promotion can be considered for this field."
        ),
        observed_value=f"Instrument: {instrument_value[:200]}",
        expected_value=f"{source_type}: {conflicting_source_value[:200]}",
        evidence_refs_json=json.dumps(evidence_refs) if evidence_refs else None,
        suggested_action=(
            "Request official clarification from the issuing bank. "
            "Do NOT promote trust level until the discrepancy is resolved by an authorized officer."
        ),
        policy_version_ref="module4_conflict_adapter_v1",
        first_detected_at=now,
        last_evaluated_at=now,
    )

    # Integration gap guard: if saving fails, propagate with a clear message
    try:
        db.add(finding)
        db.flush()
    except Exception as exc:
        raise RuntimeError(
            f"[Module 4 → Module 3 integration gap] Failed to persist conflict finding "
            f"for instrument={instrument_id}, field={field_name}: {exc}"
        ) from exc

    return ConflictRecord(
        finding_id=finding.id,
        field_name=field_name,
        instrument_value=instrument_value,
        conflicting_source_value=conflicting_source_value,
        source_type=source_type,
        source_reference=source_reference,
        detected_at=now,
    )


def report_all_response_conflicts(
    db: Session,
    instrument_id: str,
    institution_id: str,
    field_comparisons: Dict[str, Any],
    source_type: str,
    source_reference: str,
    verification_response_id: Optional[str] = None,
) -> List[ConflictRecord]:
    """
    Iterate over field_comparisons (from compare_instrument_vs_bank_values) and
    record a finding for every field where is_match is False.

    Returns list of ConflictRecords (one per mismatched field).
    Returns empty list if no mismatches exist.
    """
    conflicts: List[ConflictRecord] = []
    for field_name, comparison in field_comparisons.items():
        if comparison.get("is_match") is False:
            conflict = report_verification_conflict(
                db=db,
                instrument_id=instrument_id,
                institution_id=institution_id,
                field_name=field_name,
                instrument_value=str(comparison.get("instrument_value", "")),
                conflicting_source_value=str(comparison.get("bank_value", "")),
                source_type=source_type,
                source_reference=source_reference,
                verification_response_id=verification_response_id,
            )
            conflicts.append(conflict)
    return conflicts
