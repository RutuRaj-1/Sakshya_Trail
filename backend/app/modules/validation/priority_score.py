"""
Module 3 — Explainable Review Priority Score Engine

Provides a transparent, deterministic 0–100 review priority score designed
strictly for review queue ordering and prioritization.

Safety constraints
------------------
* This is a REVIEW-ORDERING score only, NOT an AI-predicted fraud probability
  or financial risk score.
* Never alters Instrument.trust_level.
* Never automatically approves, rejects, or releases an instrument.
* Missing or unknown input fields remain explicitly distinguishable from zero values.
* Factor weights are labeled as prototype assumptions until validated by stakeholders.
* Every score computation returns an itemized factor contribution breakdown.
"""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from app.modules.instruments.models import Instrument
from app.modules.validation.models import ValidationFinding
from app.modules.validation.enums import RuleSeverity, RuleType, FindingStatus


@dataclass
class FactorContribution:
    factor_name: str
    points: float
    max_points: float
    observed_value: Any
    is_missing: bool
    basis: str


@dataclass
class PriorityScoreResult:
    total_score: int
    score_version: str
    is_prototype: bool
    factor_breakdown: List[FactorContribution]
    missing_fields: List[str]
    disclaimer: str
    summary_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "score_version": self.score_version,
            "is_prototype": self.is_prototype,
            "factor_breakdown": [asdict(f) for f in self.factor_breakdown],
            "missing_fields": self.missing_fields,
            "disclaimer": self.disclaimer,
            "summary_explanation": self.summary_explanation,
        }


# Explicit prototype factor weight allocations (sum to 100 max)
WEIGHT_DAYS_TO_MATURITY = 25.0
WEIGHT_FINDING_SEVERITY = 30.0
WEIGHT_UNRESOLVED_DISCREPANCIES = 20.0
WEIGHT_DOCUMENT_COMPLETENESS = 15.0
WEIGHT_TRUST_DIMENSION = 10.0

SCORE_VERSION = "1.0-prototype"


def calculate_review_priority_score(
    instrument: Optional[Instrument],
    open_findings: List[ValidationFinding],
    has_fdr_copy: Optional[bool] = None,
    evaluation_date: Optional[date] = None,
) -> PriorityScoreResult:
    """
    Compute a deterministic 0–100 review queue priority score for an instrument.

    Factors:
    1. Days to maturity (Closer maturity requires more urgent officer scrutiny).
    2. Highest unresolved deterministic finding severity (Critical/High findings require immediate attention).
    3. Total count of unresolved discrepancies.
    4. Document completeness (Missing FDR certificate elevates review priority).
    5. Trust/verification dimension (Unverified L0 requires more manual scrutiny than L2/L3).
    """
    if evaluation_date is None:
        evaluation_date = date.today()

    factors: List[FactorContribution] = []
    missing_fields: List[str] = []
    total_points = 0.0

    # -------------------------------------------------------------------------
    # Factor 1: Days to Maturity (Max 25 pts)
    # -------------------------------------------------------------------------
    if instrument is None or instrument.maturity_date is None:
        missing_fields.append("maturity_date")
        factors.append(FactorContribution(
            factor_name="days_to_maturity",
            points=0.0,
            max_points=WEIGHT_DAYS_TO_MATURITY,
            observed_value=None,
            is_missing=True,
            basis="Maturity date is unknown or unavailable. No priority points assigned.",
        ))
    else:
        days_left = (instrument.maturity_date - evaluation_date).days
        if days_left < 0:
            # Overdue / expired
            pts = WEIGHT_DAYS_TO_MATURITY
            basis = f"Instrument expired {abs(days_left)} days ago (past maturity date {instrument.maturity_date}). Maximum urgency."
        elif days_left <= 30:
            pts = WEIGHT_DAYS_TO_MATURITY * 0.90  # 22.5 pts
            basis = f"Matures within 30 days ({days_left} days remaining until {instrument.maturity_date}). High review urgency."
        elif days_left <= 90:
            pts = WEIGHT_DAYS_TO_MATURITY * 0.60  # 15.0 pts
            basis = f"Matures within 90 days ({days_left} days remaining). Moderate window for regulatory scrutiny."
        elif days_left <= 180:
            pts = WEIGHT_DAYS_TO_MATURITY * 0.30  # 7.5 pts
            basis = f"Matures within 180 days ({days_left} days remaining)."
        else:
            pts = 0.0
            basis = f"Term is well in the future ({days_left} days remaining until maturity)."

        total_points += pts
        factors.append(FactorContribution(
            factor_name="days_to_maturity",
            points=round(pts, 1),
            max_points=WEIGHT_DAYS_TO_MATURITY,
            observed_value=days_left,
            is_missing=False,
            basis=basis,
        ))

    # -------------------------------------------------------------------------
    # Factor 2: Highest Finding Severity (Max 30 pts)
    # -------------------------------------------------------------------------
    severities = [f.severity for f in open_findings if f.status in (FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value)]
    if not severities:
        factors.append(FactorContribution(
            factor_name="highest_finding_severity",
            points=0.0,
            max_points=WEIGHT_FINDING_SEVERITY,
            observed_value="NONE",
            is_missing=False,
            basis="No unresolved discrepancies currently open on this instrument.",
        ))
    elif RuleSeverity.CRITICAL.value in severities:
        pts = WEIGHT_FINDING_SEVERITY
        total_points += pts
        factors.append(FactorContribution(
            factor_name="highest_finding_severity",
            points=pts,
            max_points=WEIGHT_FINDING_SEVERITY,
            observed_value="CRITICAL",
            is_missing=False,
            basis="Contains one or more unresolved CRITICAL severity findings requiring immediate inspection.",
        ))
    elif RuleSeverity.HIGH.value in severities:
        pts = WEIGHT_FINDING_SEVERITY * 0.75  # 22.5 pts
        total_points += pts
        factors.append(FactorContribution(
            factor_name="highest_finding_severity",
            points=round(pts, 1),
            max_points=WEIGHT_FINDING_SEVERITY,
            observed_value="HIGH",
            is_missing=False,
            basis="Contains unresolved HIGH severity findings requiring officer investigation.",
        ))
    elif RuleSeverity.MEDIUM.value in severities:
        pts = WEIGHT_FINDING_SEVERITY * 0.40  # 12.0 pts
        total_points += pts
        factors.append(FactorContribution(
            factor_name="highest_finding_severity",
            points=round(pts, 1),
            max_points=WEIGHT_FINDING_SEVERITY,
            observed_value="MEDIUM",
            is_missing=False,
            basis="Contains unresolved MEDIUM severity findings.",
        ))
    else:
        pts = WEIGHT_FINDING_SEVERITY * 0.15  # 4.5 pts
        total_points += pts
        factors.append(FactorContribution(
            factor_name="highest_finding_severity",
            points=round(pts, 1),
            max_points=WEIGHT_FINDING_SEVERITY,
            observed_value="LOW",
            is_missing=False,
            basis="Contains only minor or informational advisory findings.",
        ))

    # -------------------------------------------------------------------------
    # Factor 3: Total Count of Unresolved Discrepancies (Max 20 pts)
    # -------------------------------------------------------------------------
    active_count = len([f for f in open_findings if f.status in (FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value)])
    # 5 pts per active finding, capped at 20 pts (4 findings)
    pts = min(active_count * 5.0, WEIGHT_UNRESOLVED_DISCREPANCIES)
    total_points += pts
    factors.append(FactorContribution(
        factor_name="unresolved_discrepancies_count",
        points=round(pts, 1),
        max_points=WEIGHT_UNRESOLVED_DISCREPANCIES,
        observed_value=active_count,
        is_missing=False,
        basis=f"{active_count} active finding(s) awaiting review (5 points per finding, capped at 20).",
    ))

    # -------------------------------------------------------------------------
    # Factor 4: Document Completeness (Max 15 pts)
    # -------------------------------------------------------------------------
    if has_fdr_copy is None:
        missing_fields.append("has_fdr_copy")
        factors.append(FactorContribution(
            factor_name="document_completeness",
            points=0.0,
            max_points=WEIGHT_DOCUMENT_COMPLETENESS,
            observed_value=None,
            is_missing=True,
            basis="Document completeness evidence not evaluated or unknown. No points added.",
        ))
    elif not has_fdr_copy:
        pts = WEIGHT_DOCUMENT_COMPLETENESS  # 15.0 pts
        total_points += pts
        factors.append(FactorContribution(
            factor_name="document_completeness",
            points=pts,
            max_points=WEIGHT_DOCUMENT_COMPLETENESS,
            observed_value=False,
            is_missing=False,
            basis="Mandatory FDR copy certificate has not been uploaded. Elevates scrutiny priority.",
        ))
    else:
        factors.append(FactorContribution(
            factor_name="document_completeness",
            points=0.0,
            max_points=WEIGHT_DOCUMENT_COMPLETENESS,
            observed_value=True,
            is_missing=False,
            basis="FDR copy document is uploaded and present in registry.",
        ))

    # -------------------------------------------------------------------------
    # Factor 5: Trust Level Dimension (Max 10 pts)
    # -------------------------------------------------------------------------
    if instrument is None or not instrument.trust_level:
        missing_fields.append("trust_level")
        factors.append(FactorContribution(
            factor_name="trust_level_dimension",
            points=0.0,
            max_points=WEIGHT_TRUST_DIMENSION,
            observed_value=None,
            is_missing=True,
            basis="Trust level unknown. No points added.",
        ))
    else:
        tl = instrument.trust_level.upper()
        if tl.startswith("L0"):
            pts = WEIGHT_TRUST_DIMENSION  # 10.0 pts
            basis = "Instrument is at unverified declared status (L0). Requires higher review attention."
        elif tl.startswith("L1"):
            pts = WEIGHT_TRUST_DIMENSION * 0.50  # 5.0 pts
            basis = "Instrument is document-consistent (L1) but not yet officer-verified."
        else:
            pts = 0.0
            basis = f"Instrument has already attained verified status ({tl}). Low prioritization needed."

        total_points += pts
        factors.append(FactorContribution(
            factor_name="trust_level_dimension",
            points=round(pts, 1),
            max_points=WEIGHT_TRUST_DIMENSION,
            observed_value=instrument.trust_level,
            is_missing=False,
            basis=basis,
        ))

    final_score = int(round(min(100.0, max(0.0, total_points))))

    summary = (
        f"Review priority score: {final_score}/100 based on {len(factors)} transparent factors. "
        f"Primary drivers: {', '.join(f.factor_name for f in factors if f.points >= 10.0) or 'baseline'}. "
        "Intended strictly for officer review queue ordering."
    )

    return PriorityScoreResult(
        total_score=final_score,
        score_version=SCORE_VERSION,
        is_prototype=True,
        factor_breakdown=factors,
        missing_fields=missing_fields,
        disclaimer=(
            "This priority score is a transparent, deterministic review-ordering metric only. "
            "It does NOT represent an AI-predicted fraud probability, credit rating, or financial risk score. "
            "It does not alter trust levels, reject submissions, or replace human officer judgment."
        ),
        summary_explanation=summary,
    )
