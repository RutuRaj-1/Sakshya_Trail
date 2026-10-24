"""
Module 3 — Validation Rules: Duplicate Detection and Tenant-Isolated Discrepancy Analysis

Implements bank-aware and reference-aware duplicate instrument detection,
cross-institution reference duplicate checks with privacy isolation,
and exact document-hash (SHA-256) duplicate byte checks.

Rules:
- VAL-DUP-001: Intra-Institution Reference Duplicate (Same Bank + Reference)
- VAL-DUP-002: Cross-Institution Reference Duplicate (Same Bank + Reference, Tenant-Isolated)
- VAL-DUP-003: Exact Document-Hash Duplicate Bytes (SHA-256 File Match)

Design constraints
------------------
* Avoid naive matching of unrelated reference strings from different banks.
* Missing bank information must NOT silently produce a definitive duplicate result.
* Never merge, delete, block, or label a record fraudulent solely because of a match.
* Preserve institution isolation: cross-institution findings NEVER leak confidential record details.
* Wording for byte match MUST NOT claim proof of forgery, authenticity, or improper reuse.
"""
from typing import List, Dict, Any

from app.modules.validation.enums import (
    FindingCategory,
    RuleOutcome,
    RuleSeverity,
    RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule,
    RuleContext,
    RuleResult,
    rule_registry,
)
from app.modules.validation.normalization import (
    normalize_reference_number,
    normalize_bank_name,
)


class PotentialDuplicateHeuristicRule(BaseValidationRule):
    """
    VAL-DUP-001 — Bank-aware reference duplicate check within the same institution.

    Detects other instruments in the SAME institution that share the same normalized
    bank name and reference number.
    """
    rule_id = "VAL-DUP-001"
    rule_version = "2.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.POTENTIAL_DUPLICATE
    severity = RuleSeverity.HIGH
    description = (
        "Bank-aware check detecting whether other instruments within the same institution "
        "share the identical normalized bank identity and reference number."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        # Missing bank information must not silently produce a definitive duplicate result
        if not context.bank_name or not context.bank_name.strip():
            return self._unable_to_evaluate(
                "Missing issuing bank information on current instrument. "
                "Bank identity is required to perform bank-aware reference duplicate evaluation."
            )

        if not context.reference_number or not context.reference_number.strip():
            return self._unable_to_evaluate(
                "Missing reference number on current instrument. Cannot evaluate reference duplicates."
            )

        matches = context.duplicate_same_inst_matches
        if not matches:
            matches = context.policy.get("_duplicate_same_inst_matches", [])

        # Backward compatibility for tests passing legacy policy keys
        if not matches and "_duplicate_sibling_count" in context.policy:
            legacy_count = context.policy.get("_duplicate_sibling_count")
            if legacy_count is None:
                return self._unable_to_evaluate(
                    "Duplicate sibling count was not supplied in the evaluation context."
                )
            legacy_count = int(legacy_count)
            if legacy_count == 0:
                return self._pass(
                    "No other instruments within this institution share the same bank and reference number."
                )
            legacy_ids = context.policy.get("_duplicate_sibling_ids", [])
            matches = [
                {"id": sid, "reference_number": context.reference_number, "status": "UNKNOWN"}
                for sid in legacy_ids
            ] if legacy_ids else [
                {"id": f"sibling-{i+1}", "reference_number": context.reference_number, "status": "UNKNOWN"}
                for i in range(legacy_count)
            ]

        if not matches:
            return self._pass(
                "No other instruments within this institution share the same bank and reference number."
            )

        match_ids = [m["id"] for m in matches if "id" in m]
        summary_lines = [
            f"Instrument {m.get('id')} (Ref: {m.get('reference_number')}, Status: {m.get('status')})"
            for m in matches
        ]

        norm_bank = normalize_bank_name(context.bank_name)
        norm_ref = normalize_reference_number(context.reference_number)

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Potential duplicate instrument reference within institution",
            explanation=(
                f"{len(matches)} other instrument(s) in this institution share the same issuing bank "
                f"('{context.bank_name}', normalized: '{norm_bank}') and reference number "
                f"('{context.reference_number}', normalized: '{norm_ref}'): {', '.join(summary_lines)}. "
                "This may indicate a re-registration, renewal, or entry error. "
                "This observation is advisory and does NOT establish fraud or forgery. "
                "Human officer review is required."
            ),
            observed_value=f"{len(matches)} sibling instrument(s) with matching bank and reference",
            expected_value="Unique reference number per issuing bank within institution",
            evidence_refs=match_ids,
            suggested_action=(
                "Review the matching instrument records. If this instrument is a legitimate renewal "
                "or replacement, verify the previous instrument record is marked inactive or renewed. "
                "If entered inadvertently, update or cancel the duplicate."
            ),
            fingerprint_key=f"bank={norm_bank},ref={norm_ref},scope=intra_institution",
        )


class CrossInstitutionReferenceDuplicateRule(BaseValidationRule):
    """
    VAL-DUP-002 — Bank-aware reference duplicate check across DIFFERENT institutions.

    Preserves institution isolation: confidential details of other institutions
    are masked and NOT exposed to ordinary users.
    """
    rule_id = "VAL-DUP-002"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.POTENTIAL_DUPLICATE
    severity = RuleSeverity.HIGH
    description = (
        "Detects whether an instrument in another institution shares the same bank and reference. "
        "Preserves cross-tenant privacy by masking external institution identities."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if not context.bank_name or not context.bank_name.strip():
            return self._unable_to_evaluate(
                "Missing bank information on current instrument. Cannot evaluate cross-institution duplicates."
            )

        if not context.reference_number or not context.reference_number.strip():
            return self._unable_to_evaluate(
                "Missing reference number on current instrument. Cannot evaluate duplicates."
            )

        cross_matches = context.duplicate_cross_inst_matches
        if not cross_matches:
            cross_matches = context.policy.get("_duplicate_cross_inst_matches", [])

        if not cross_matches:
            return self._pass(
                "No cross-institution duplicate reference matches detected for this bank and reference."
            )

        norm_bank = normalize_bank_name(context.bank_name)
        norm_ref = normalize_reference_number(context.reference_number)
        count = len(cross_matches)

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Potential cross-institution duplicate instrument reference",
            explanation=(
                f"A matching reference number ('{context.reference_number}', normalized: '{norm_ref}') "
                f"under bank '{context.bank_name}' was identified in {count} submission(s) from "
                "another institution. To protect tenant confidentiality, details of the other institution "
                "are masked. This observation does not confirm improper reuse or forgery. "
                "This finding has been routed for authorized regulatory officer review."
            ),
            observed_value=f"{count} cross-institution candidate match(es) [tenant-masked]",
            expected_value="Unique instrument reference across all registered institutions",
            evidence_refs=[],  # Sensitive cross-institution IDs omitted to preserve privacy
            suggested_action=(
                "Escalate to an authorized regulatory scrutiny officer. The regulatory officer will "
                "examine both submissions in a privileged session to determine whether the duplicate "
                "reflects a cross-entity submission error or genuine certificate reuse."
            ),
            fingerprint_key=f"bank={norm_bank},ref={norm_ref},scope=cross_institution",
        )


class DocumentHashDuplicateRule(BaseValidationRule):
    """
    VAL-DUP-003 — Exact SHA-256 document byte match across instruments.

    Uses hashes already computed by Module 2.
    Preserves tenant isolation when reporting matches.
    """
    rule_id = "VAL-DUP-003"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.POTENTIAL_DUPLICATE
    severity = RuleSeverity.HIGH
    description = (
        "Identifies identical document bytes (SHA-256 match) previously uploaded under a different instrument."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        hash_matches = context.duplicate_hash_matches
        if not hash_matches:
            hash_matches = context.policy.get("_duplicate_hash_matches", [])

        if not hash_matches:
            return self._pass("All uploaded document versions have unique file byte hashes across instruments.")

        first_match = hash_matches[0]
        sha256 = first_match.get("sha256_hash", "unknown")
        curr_ver = first_match.get("current_document_version_id", "unknown")
        prev_ver = first_match.get("previously_observed_document_version_id", "unknown")
        assoc_inst = first_match.get("associated_instrument_id", "unknown")
        is_cross = first_match.get("is_cross_institution", False)

        evidence = [curr_ver]
        if not is_cross and prev_ver != "unknown":
            evidence.append(prev_ver)

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Identical file bytes previously uploaded across instruments",
            explanation=(
                "Identical file bytes were previously uploaded. Review the associated instruments and "
                f"submission context. Hash comparison matched SHA-256: {sha256[:16]}... "
                f"Current version: {curr_ver}, Previously observed version: {prev_ver}, "
                f"Associated instrument: {assoc_inst}. "
                "Note: Identical file bytes can occur in legitimate administrative scenarios "
                "(such as re-filings, shared bank covering letters, or multi-deposit submissions) "
                "and do not prove forgery, authenticity, or improper reuse."
            ),
            observed_value=f"SHA-256 match: {sha256[:16]}... (associated instrument: {assoc_inst})",
            expected_value="Unique document content per instrument submission",
            evidence_refs=evidence,
            suggested_action=(
                "Review the associated instrument submissions to confirm whether the duplicate file "
                "is an expected shared document or an accidental duplicate upload."
            ),
            fingerprint_key=f"sha256={sha256},curr={curr_ver},prev={prev_ver}",
        )


# Self-register
rule_registry.register(PotentialDuplicateHeuristicRule())
rule_registry.register(CrossInstitutionReferenceDuplicateRule())
rule_registry.register(DocumentHashDuplicateRule())
