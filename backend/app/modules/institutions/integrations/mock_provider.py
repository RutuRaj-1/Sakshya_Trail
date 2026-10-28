"""
Institutional Verification Provider - Deterministic Mock Implementation
Provides reproducible verification results for demonstration, testing, and SIH jury evaluation
based on known AICTE handbook institution records.
Does NOT contact live regulatory servers. Explicitly labeled as SIMULATED / MOCK.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.modules.institutions.integrations.base import (
    InstitutionVerificationProvider,
    InstitutionVerificationResult,
)

# Reference catalog of mock AICTE registered institutions for deterministic tests/demos
KNOWN_AICTE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "1-10924811": {
        "legal_name": "Government Engineering College, Bilaspur",
        "state": "Chhattisgarh",
        "status": "APPROVED",
        "institution_type": "GOVERNMENT_INSTITUTE",
        "handbook_year": "2025-2026",
    },
    "1-45678901": {
        "legal_name": "Delhi Technological University",
        "state": "Delhi",
        "status": "APPROVED",
        "institution_type": "STATE_UNIVERSITY",
        "handbook_year": "2025-2026",
    },
    "1-98765432": {
        "legal_name": "Vellore Institute of Technology",
        "state": "Tamil Nadu",
        "status": "APPROVED",
        "institution_type": "DEEMED_UNIVERSITY",
        "handbook_year": "2025-2026",
    },
    "1-99999999": {
        "legal_name": "Defunct Technical Academy",
        "state": "Maharashtra",
        "status": "WITHDRAWN",
        "institution_type": "PRIVATE_INSTITUTE",
        "handbook_year": "2023-2024",
    },
}


class MockInstitutionVerificationProvider(InstitutionVerificationProvider):
    """
    Mock adapter returning deterministic institutional approval status.
    """

    def verify_institution(
        self,
        institution_code: str,
        legal_name: str,
        expected_state: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> InstitutionVerificationResult:
        corr_id = correlation_id or f"AICTE-MOCK-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc)

        code_clean = institution_code.strip()
        record = KNOWN_AICTE_REGISTRY.get(code_clean)

        # 1. Unrecognized Institution Code
        if not record:
            # If name matches a synthetic pattern or code is unknown
            return InstitutionVerificationResult(
                is_verified=False,
                status="MISMATCH",
                provider_name="AICTE Institutional Registry (Simulated Mock)",
                environment="mock",
                correlation_id=corr_id,
                timestamp=now,
                verified_fields={},
                mismatched_fields={
                    "code": {
                        "submitted": code_clean,
                        "registry": None,
                        "reason": f"Institution code '{code_clean}' not found in mock AICTE registry database.",
                    }
                },
                unsupported_fields=["pan_card", "land_registration_number"],
                official_approval_status="UNKNOWN",
                notes="Simulated mock response. Record not found in offline mock dataset.",
                raw_metadata={"simulated": True, "lookup_key": code_clean},
            )

        # 2. Known Record Comparison
        verified_fields = {"code": code_clean}
        mismatched_fields = {}

        # Legal Name comparison (case-insensitive substring/equality)
        reg_name = record["legal_name"]
        if reg_name.lower() in legal_name.lower() or legal_name.lower() in reg_name.lower():
            verified_fields["legal_name"] = reg_name
        else:
            mismatched_fields["legal_name"] = {
                "submitted": legal_name,
                "registry": reg_name,
                "reason": "Submitted institution legal name does not match official AICTE registry entry.",
            }

        # State comparison
        if expected_state:
            reg_state = record["state"]
            if expected_state.lower().strip() == reg_state.lower().strip():
                verified_fields["state"] = reg_state
            else:
                mismatched_fields["state"] = {
                    "submitted": expected_state,
                    "registry": reg_state,
                    "reason": "Submitted state location does not match official AICTE registered jurisdiction.",
                }

        approval_status = record.get("status", "APPROVED")
        verified_fields["approval_status"] = approval_status
        verified_fields["institution_type"] = record.get("institution_type")

        is_match = len(mismatched_fields) == 0 and approval_status == "APPROVED"
        status_code = "MATCH" if is_match else "MISMATCH"

        return InstitutionVerificationResult(
            is_verified=is_match,
            status=status_code,
            provider_name="AICTE Institutional Registry (Simulated Mock)",
            environment="mock",
            correlation_id=corr_id,
            timestamp=now,
            verified_fields=verified_fields,
            mismatched_fields=mismatched_fields,
            unsupported_fields=["pan_card", "land_registration_number"],
            official_approval_status=approval_status,
            handbook_year=record.get("handbook_year"),
            notes=(
                "Simulated mock evaluation for demonstration. "
                "Verified against offline test fixtures. Does not contact production AICTE systems."
            ),
            raw_metadata={"simulated": True, "fixture_record": record},
        )

