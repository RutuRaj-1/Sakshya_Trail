"""
Module 5 — Prompt 4: Lineage Continuity & Gap/Overlap Assessment Service
Evaluates date continuity between predecessor and successor instruments under policy-governed semantics.
Integrates directly with Module 3 ValidationFinding service to surface discrepancies without altering trust.
"""
import uuid
import json
import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.base import get_utc_now
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import LifecyclePolicy, InstrumentLineage
from app.modules.lifecycle.enums import (
    RenewalComparisonMethod,
    ContinuityIndicator,
    ContinuityOutcome,
)
from app.modules.validation.models import ValidationFinding
from app.modules.validation.enums import (
    FindingCategory,
    FindingStatus,
    RuleSeverity,
    RuleType,
)


@dataclass
class ContinuityAssessmentResult:
    predecessor_id: str
    successor_id: str
    dates_compared: Dict[str, Optional[str]]
    date_source_fields: Dict[str, str]
    comparison_semantics: str
    gap_days: Optional[int]
    overlap_days: Optional[int]
    policy_version: Optional[int]
    outcome: ContinuityOutcome
    continuity_indicator: ContinuityIndicator
    explanation: str
    is_provisional: bool
    detector_type: str = "DETERMINISTIC"
    finding_id: Optional[str] = None
    evaluated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predecessor_id": self.predecessor_id,
            "successor_id": self.successor_id,
            "dates_compared": self.dates_compared,
            "date_source_fields": self.date_source_fields,
            "comparison_semantics": self.comparison_semantics,
            "gap_days": self.gap_days,
            "overlap_days": self.overlap_days,
            "policy_version": self.policy_version,
            "outcome": self.outcome.value,
            "continuity_indicator": self.continuity_indicator.value,
            "explanation": self.explanation,
            "is_provisional": self.is_provisional,
            "detector_type": self.detector_type,
            "finding_id": self.finding_id,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }


def assess_lineage_continuity(
    db: Session,
    predecessor: Instrument,
    successor: Instrument,
    policy: Optional[LifecyclePolicy] = None,
    create_finding: bool = True,
) -> ContinuityAssessmentResult:
    """
    Transparently evaluates continuity between predecessor and successor instruments.
    Rules:
    1. Examines predecessor.maturity_date against successor's valid-from date.
    2. If successor.effective_date is available, it is prioritized.
    3. If successor.effective_date is unavailable, successor.issue_date is used ONLY IF
       the active policy explicitly configures PROVISIONAL_ISSUE_DATE or ISSUE_DATE_TO_MATURITY_DATE.
    4. If effective date is unavailable under STRICT_CONTINUOUS_TERM, returns CONTINUITY_UNDETERMINED.
    5. Missing/unconfigured policy returns POLICY_UNCONFIGURED.
    6. Potential gap/overlap exceeding configured tolerance creates a Module 3 ValidationFinding.
    """
    now = get_utc_now()
    pred_maturity = predecessor.maturity_date

    # 1. Check for unconfigured policy
    if policy is None:
        return ContinuityAssessmentResult(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
            dates_compared={
                "predecessor_maturity_date": pred_maturity.isoformat() if pred_maturity else None,
                "successor_comparison_date": None,
            },
            date_source_fields={
                "predecessor": "predecessor.maturity_date",
                "successor": "UNCONFIGURED_POLICY",
            },
            comparison_semantics="NONE",
            gap_days=None,
            overlap_days=None,
            policy_version=None,
            outcome=ContinuityOutcome.POLICY_UNCONFIGURED,
            continuity_indicator=ContinuityIndicator.UNKNOWN,
            explanation="Continuity cannot be evaluated because no active or applicable lifecycle policy was configured.",
            is_provisional=False,
            evaluated_at=now,
        )

    # 2. Determine successor comparison date according to policy semantics
    succ_comparison_date: Optional[date] = None
    succ_source_field: str = ""
    is_provisional: bool = False

    succ_effective = getattr(successor, "effective_date", None)
    if succ_effective is not None:
        succ_comparison_date = succ_effective
        succ_source_field = "successor.effective_date"
        is_provisional = False
    else:
        # Check policy allowance for provisional proxy
        if policy.renewal_comparison_method in (
            RenewalComparisonMethod.PROVISIONAL_ISSUE_DATE.value,
            RenewalComparisonMethod.ISSUE_DATE_TO_MATURITY_DATE.value,
        ):
            succ_comparison_date = successor.issue_date
            succ_source_field = "successor.issue_date (PROVISIONAL_PROXY)"
            is_provisional = True
        else:
            # Under STRICT_CONTINUOUS_TERM, issue date is NOT permitted as proxy
            succ_comparison_date = None
            succ_source_field = "successor.effective_date (UNAVAILABLE)"
            is_provisional = False

    dates_compared = {
        "predecessor_maturity_date": pred_maturity.isoformat() if pred_maturity else None,
        "successor_comparison_date": succ_comparison_date.isoformat() if succ_comparison_date else None,
    }
    date_source_fields = {
        "predecessor": "predecessor.maturity_date",
        "successor": succ_source_field,
    }

    # 3. Handle undetermined date inputs
    if pred_maturity is None or succ_comparison_date is None:
        return ContinuityAssessmentResult(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
            dates_compared=dates_compared,
            date_source_fields=date_source_fields,
            comparison_semantics=policy.renewal_comparison_method,
            gap_days=None,
            overlap_days=None,
            policy_version=policy.version,
            outcome=ContinuityOutcome.CONTINUITY_UNDETERMINED,
            continuity_indicator=ContinuityIndicator.UNKNOWN,
            explanation=(
                f"Actual effective validity start date is unavailable on successor instrument '{successor.id}'. "
                f"Issue date is not authorized as a proxy under policy comparison semantics '{policy.renewal_comparison_method}'."
            ),
            is_provisional=is_provisional,
            evaluated_at=now,
        )

    # 4. Compute differences
    diff_days = (succ_comparison_date - pred_maturity).days
    finding_id: Optional[str] = None

    if diff_days > 0:
        gap_days = diff_days
        overlap_days = 0
        if gap_days <= policy.max_allowed_gap_days:
            outcome = ContinuityOutcome.CONTINUITY_WITHIN_CONFIGURED_TOLERANCE
            indicator = ContinuityIndicator.CONTINUOUS
            explanation = (
                f"Validity gap of {gap_days} day(s) is within configured policy tolerance "
                f"({policy.max_allowed_gap_days} day(s))."
            )
        else:
            outcome = ContinuityOutcome.POTENTIAL_GAP
            indicator = ContinuityIndicator.GAP_DETECTED
            explanation = (
                f"Potential validity gap of {gap_days} day(s) exceeds policy tolerance "
                f"({policy.max_allowed_gap_days} day(s)). Predecessor matured on {pred_maturity.isoformat()}, "
                f"successor begins on {succ_comparison_date.isoformat()} ({succ_source_field})."
            )

    elif diff_days < 0:
        gap_days = 0
        overlap_days = abs(diff_days)
        if overlap_days <= policy.max_allowed_overlap_days:
            outcome = ContinuityOutcome.CONTINUITY_WITHIN_CONFIGURED_TOLERANCE
            indicator = ContinuityIndicator.CONTINUOUS
            explanation = (
                f"Validity overlap of {overlap_days} day(s) is within configured policy tolerance "
                f"({policy.max_allowed_overlap_days} day(s))."
            )
        else:
            outcome = ContinuityOutcome.POTENTIAL_OVERLAP
            indicator = ContinuityIndicator.OVERLAP_DETECTED
            explanation = (
                f"Potential validity overlap of {overlap_days} day(s) exceeds policy tolerance "
                f"({policy.max_allowed_overlap_days} day(s)). Predecessor matures on {pred_maturity.isoformat()}, "
                f"successor begins on {succ_comparison_date.isoformat()} ({succ_source_field})."
            )
    else:
        gap_days = 0
        overlap_days = 0
        outcome = ContinuityOutcome.CONTINUITY_WITHIN_CONFIGURED_TOLERANCE
        indicator = ContinuityIndicator.CONTINUOUS
        explanation = (
            f"Seamless continuous term with 0 gap and 0 overlap between predecessor maturity "
            f"and successor effective start ({pred_maturity.isoformat()})."
        )

    # 5. Module 3 Finding Integration for out-of-tolerance gap/overlap
    if create_finding and outcome in (ContinuityOutcome.POTENTIAL_GAP, ContinuityOutcome.POTENTIAL_OVERLAP):
        try:
            finding = _create_or_update_continuity_finding(
                db=db,
                successor=successor,
                predecessor=predecessor,
                outcome=outcome,
                gap_days=gap_days,
                overlap_days=overlap_days,
                explanation=explanation,
                policy=policy,
            )
            if finding:
                finding_id = finding.id
        except Exception:
            # Finding creation failure should not abort lineage creation
            pass

    return ContinuityAssessmentResult(
        predecessor_id=predecessor.id,
        successor_id=successor.id,
        dates_compared=dates_compared,
        date_source_fields=date_source_fields,
        comparison_semantics=policy.renewal_comparison_method,
        gap_days=gap_days,
        overlap_days=overlap_days,
        policy_version=policy.version,
        outcome=outcome,
        continuity_indicator=indicator,
        explanation=explanation,
        is_provisional=is_provisional,
        finding_id=finding_id,
        evaluated_at=now,
    )


def _create_or_update_continuity_finding(
    db: Session,
    successor: Instrument,
    predecessor: Instrument,
    outcome: ContinuityOutcome,
    gap_days: Optional[int],
    overlap_days: Optional[int],
    explanation: str,
    policy: LifecyclePolicy,
) -> Optional[ValidationFinding]:
    """
    Integrates with Module 3 by creating or updating an audited ValidationFinding record.
    Never alters trust levels or marks instruments invalid.
    """
    rule_id = f"LINEAGE_CONTINUITY_{outcome.value}"
    fingerprint_raw = f"{successor.id}:{predecessor.id}:{rule_id}:{policy.version}"
    fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()
    now = get_utc_now()

    # Check for existing open finding with this fingerprint
    existing = db.scalar(
        select(ValidationFinding).where(
            and_(
                ValidationFinding.instrument_id == successor.id,
                ValidationFinding.finding_fingerprint == fingerprint,
                ValidationFinding.status.in_([FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value]),
            )
        )
    )

    if existing:
        existing.last_evaluated_at = now
        existing.explanation = explanation
        db.commit()
        return existing

    severity = (
        RuleSeverity.HIGH.value
        if outcome == ContinuityOutcome.POTENTIAL_GAP
        else RuleSeverity.MEDIUM.value
    )

    finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=fingerprint,
        instrument_id=successor.id,
        institution_id=successor.institution_id,
        rule_id=rule_id,
        rule_version=str(policy.version),
        rule_type=RuleType.DETERMINISTIC.value,
        category=FindingCategory.POLICY_COMPLIANCE.value,
        severity=severity,
        status=FindingStatus.OPEN.value,
        title=f"Statutory Lineage Continuity: {outcome.value.replace('_', ' ')}",
        explanation=explanation,
        observed_value=f"Gap: {gap_days}d, Overlap: {overlap_days}d",
        expected_value=f"Max Gap: {policy.max_allowed_gap_days}d, Max Overlap: {policy.max_allowed_overlap_days}d",
        evidence_refs_json=json.dumps([predecessor.id, successor.id]),
        suggested_action="Review validity continuity with institution and bank deposit records.",
        policy_version_ref=f"policy_v{policy.version}",
        first_detected_at=now,
        last_evaluated_at=now,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding
