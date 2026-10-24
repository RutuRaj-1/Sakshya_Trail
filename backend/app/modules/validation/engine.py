"""
Module 3 — Validation Orchestration Engine

The engine is the single entry point for running validation rules
against an instrument. It:

1. Builds the RuleContext from DB-sourced instrument and document data.
2. Populates policy from the policy service.
3. Computes duplicate sibling count for the heuristic rule.
4. Executes each enabled rule in isolation (exceptions are caught per-rule).
5. Persists FAIL/WARNING findings via the finding service.
6. Resolves previously open findings for rules that now PASS.
7. Creates a ValidationRun log record.

Safety guarantees
-----------------
* Does NOT modify Instrument.trust_level.
* Does NOT approve or reject releases.
* One failed optional rule does NOT prevent others from running.
* Returns structured results for every rule, with UNABLE_TO_EVALUATE
  for any rule that raises an unexpected exception.
* PASS / NOT_APPLICABLE outcomes resolve any previously open findings.
"""
import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.instruments.models import Instrument
from app.modules.institutions.models import Institution
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationRun
from app.modules.validation.enums import RuleOutcome
from app.modules.validation.registry import (
    BaseValidationRule,
    RuleContext,
    RuleResult,
    rule_registry,
)
from app.modules.validation.policy_service import build_policy_context
from app.modules.validation.finding_service import (
    upsert_finding,
    resolve_finding_if_cleared,
)
from app.common.exceptions import NotFoundException


def _build_context(
    db: Session,
    instrument: Instrument,
    triggered_by_user_id: Optional[str],
    run_id: Optional[str],
) -> RuleContext:
    """
    Assemble a read-only RuleContext from live database data.

    Document metadata is included (without content) so rules can check
    category presence and processing status.
    """
    institution = db.scalar(
        select(Institution).where(Institution.id == instrument.institution_id)
    )

    # --- Duplicate sibling count ---
    sibling_count = 0
    sibling_ids: List[str] = []
    norm_bank = (instrument.bank_name or "").strip().lower()
    norm_ref = (instrument.reference_number or "").strip().lower()

    siblings = db.scalars(
        select(Instrument).where(
            func.lower(func.trim(Instrument.bank_name)) == norm_bank,
            func.lower(func.trim(Instrument.reference_number)) == norm_ref,
            Instrument.id != instrument.id,
        )
    ).all()
    sibling_count = len(siblings)
    sibling_ids = [s.id for s in siblings]

    # --- Policy context ---
    policy = build_policy_context(
        db=db,
        institution_id=instrument.institution_id,
        instrument_id=instrument.id,
        sibling_count=sibling_count,
        sibling_ids=sibling_ids,
    )

    # --- Document metadata (safe, no content) ---
    docs: List[Dict[str, Any]] = []
    db_docs = db.scalars(
        select(Document).where(Document.instrument_id == instrument.id)
    ).all()
    for doc in db_docs:
        # Use current_version if available, else most recent version
        version: Optional[DocumentVersion] = None
        if doc.current_version_id:
            version = db.scalar(
                select(DocumentVersion).where(DocumentVersion.id == doc.current_version_id)
            )
        if not version:
            version = db.scalar(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == doc.id)
                .order_by(DocumentVersion.version_number.desc())
            )

        docs.append({
            "document_id": doc.id,
            "document_version_id": version.id if version else None,
            "category": doc.category,
            "status": doc.status,
            "processing_status": version.processing_status if version else None,
            "sha256_hash": version.sha256_hash if version else None,
            "uploaded_at": version.uploaded_at.isoformat() if version else None,
        })

    # --- Document extracted fields metadata (from OCR/pipeline, if available) ---
    from app.modules.validation.extracted_fields_service import get_extracted_fields_for_instrument
    extracted_records = get_extracted_fields_for_instrument(db, instrument.id)
    extracted_fields: List[Dict[str, Any]] = []
    for rec in extracted_records:
        extracted_fields.append({
            "document_version_id": rec.document_version_id,
            "document_id": rec.document_id,
            "doc_bank_name": rec.doc_bank_name,
            "doc_reference_number": rec.doc_reference_number,
            "doc_amount_str": rec.doc_amount_str,
            "doc_issue_date_str": rec.doc_issue_date_str,
            "doc_maturity_date_str": rec.doc_maturity_date_str,
            "doc_account_holder": rec.doc_account_holder,
            "doc_lien_holder": rec.doc_lien_holder,
            "confidence_overall": rec.confidence_overall,
            "extraction_status": rec.extraction_status,
        })

    return RuleContext(
        instrument_id=instrument.id,
        institution_id=instrument.institution_id,
        instrument_status=instrument.status,
        instrument_trust_level=instrument.trust_level,
        instrument_type=instrument.instrument_type,
        bank_name=instrument.bank_name,
        branch=instrument.branch,
        reference_number=instrument.reference_number,
        amount_decimal=instrument.amount,
        currency=instrument.currency,
        issue_date=instrument.issue_date,
        maturity_date=instrument.maturity_date,
        lien_holder=instrument.lien_holder,
        lien_details=instrument.lien_details,
        lien_marked=instrument.lien_marked,
        joint_with_aicte=instrument.joint_with_aicte,
        assigned_office=instrument.assigned_office,
        institution_is_active=institution.is_active if institution else False,
        institution_type=institution.institution_type if institution else "UNKNOWN",
        institution_legal_name=institution.legal_name if institution else None,
        institution_code=institution.code if institution else None,
        available_documents=docs,
        checklist_result=None,  # Module 2 checklist result if configured / instantiated
        extracted_fields=extracted_fields,
        policy=policy,
        existing_open_findings=[],
        triggered_by_user_id=triggered_by_user_id,
        run_id=run_id,
    )


def run_validation(
    db: Session,
    instrument_id: str,
    triggered_by_user_id: Optional[str] = None,
    rule_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute validation rules for a given instrument.

    Parameters
    ----------
    instrument_id : str
        UUID of the instrument to evaluate.
    triggered_by_user_id : Optional[str]
        User who triggered the run (None = system-triggered sweep).
    rule_ids : Optional[List[str]]
        If provided, only run the specified rules; otherwise run all enabled rules.
    category : Optional[str]
        If provided, only run rules matching the given finding category.

    Returns
    -------
    Dict with keys:
        run_id, instrument_id, outcomes (list), summary (counts), new_findings_count,
        resolved_findings_count, policy_version_ref, rules_evaluated.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{instrument_id}' not found.")

    # Determine rules to run
    rules = rule_registry.get_enabled_rules()
    if rule_ids:
        rule_id_set = set(rule_ids)
        rules = [r for r in rules if r.rule_id in rule_id_set]
    if category:
        cat_norm = category.strip().upper()
        rules = [r for r in rules if r.category.value == cat_norm or r.category.name == cat_norm]

    # Create a ValidationRun record (before results so we have an ID)
    run = ValidationRun(
        instrument_id=instrument_id,
        triggered_by_user_id=triggered_by_user_id,
        rules_evaluated_csv=",".join(r.rule_id for r in rules),
        run_status="RUNNING",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Build context
    context = _build_context(db, instrument, triggered_by_user_id, run.id)

    outcomes: List[Dict[str, Any]] = []
    outcome_counts: Dict[str, int] = {o.value: 0 for o in RuleOutcome}
    new_findings = 0
    resolved_findings = 0

    for rule in rules:
        try:
            result: RuleResult = rule.evaluate(context)
        except Exception as exc:
            tb = traceback.format_exc()
            result = RuleResult(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                rule_type=rule.rule_type,
                outcome=RuleOutcome.UNABLE_TO_EVALUATE,
                category=rule.category,
                severity=rule.severity,
                title="Unable to Evaluate",
                explanation=(
                    f"An unexpected error occurred while evaluating rule {rule.rule_id}: "
                    f"{type(exc).__name__}: {exc}"
                ),
                fingerprint_key="exception",
            )

        outcome_counts[result.outcome.value] = outcome_counts.get(result.outcome.value, 0) + 1

        # Persist findings for FAIL / WARNING
        if result.is_finding:
            finding = upsert_finding(
                db=db,
                instrument_id=instrument_id,
                institution_id=instrument.institution_id,
                rule_result=result,
                validation_run_id=run.id,
                triggered_by_user_id=triggered_by_user_id,
            )
            if finding:
                new_findings += 1
        elif result.outcome in (RuleOutcome.PASS, RuleOutcome.NOT_APPLICABLE):
            # Resolve previously open findings for this rule
            resolved_findings += resolve_finding_if_cleared(
                db=db,
                instrument_id=instrument_id,
                rule_id=result.rule_id,
                rule_version=result.rule_version,
                fingerprint_key=result.fingerprint_key,
                resolution_note=(
                    f"Condition cleared on re-evaluation (outcome: {result.outcome.value})."
                ),
                resolved_by_user_id=triggered_by_user_id,
            )

        outcomes.append({
            "rule_id": result.rule_id,
            "rule_version": result.rule_version,
            "rule_type": result.rule_type.value,
            "outcome": result.outcome.value,
            "category": result.category.value,
            "severity": result.severity.value,
            "title": result.title,
            "explanation": result.explanation,
            "observed_value": result.observed_value,
            "expected_value": result.expected_value,
            "suggested_action": result.suggested_action,
            "evidence_refs": result.evidence_refs,
            "policy_version_ref": result.policy_version_ref,
            "evaluated_at": result.evaluated_at.isoformat(),
        })

    # Update run log
    policy_version_ref = context.policy.get("_policy_version_ref", "no-policy")
    run.outcome_summary_json = json.dumps(outcome_counts)
    run.new_findings_count = new_findings
    run.resolved_findings_count = resolved_findings
    run.policy_version_ref = policy_version_ref
    run.run_status = "COMPLETED"
    db.commit()
    db.refresh(run)

    # Safety assertion: no rule execution may modify trust_level
    refreshed = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    assert refreshed.trust_level == instrument.trust_level, (
        "SAFETY VIOLATION: validation engine must not modify instrument trust_level"
    )

    return {
        "run_id": run.id,
        "instrument_id": instrument_id,
        "outcomes": outcomes,
        "summary": outcome_counts,
        "rules_evaluated": [r.rule_id for r in rules],
        "passes_count": outcome_counts.get(RuleOutcome.PASS.value, 0),
        "failures_count": outcome_counts.get(RuleOutcome.FAIL.value, 0),
        "warnings_count": outcome_counts.get(RuleOutcome.WARNING.value, 0),
        "not_applicable_count": outcome_counts.get(RuleOutcome.NOT_APPLICABLE.value, 0),
        "unable_to_evaluate_count": outcome_counts.get(RuleOutcome.UNABLE_TO_EVALUATE.value, 0),
        "new_findings_count": new_findings,
        "resolved_findings_count": resolved_findings,
        "policy_version_ref": policy_version_ref,
        "run_at": run.run_at.isoformat(),
    }


def trigger_post_save_validation(
    db: Session,
    instrument_id: str,
    triggered_by_user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Safe post-save evaluation trigger after an instrument is created or materially edited.
    Executes all enabled validation rules without circular dependencies or blocking failures.
    Exceptions are logged and suppressed so normal instrument operations never fail.
    """
    try:
        return run_validation(
            db=db,
            instrument_id=instrument_id,
            triggered_by_user_id=triggered_by_user_id,
        )
    except Exception as exc:
        import logging
        logging.getLogger("fdr_sentinel.validation").warning(
            f"Post-save validation trigger failed gracefully for instrument '{instrument_id}': {exc}"
        )
        return None
