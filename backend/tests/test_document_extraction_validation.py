"""
SakshyaTrail — Document Extraction & Validation Integration Test Suite (Prompt 5)

Verifies:
1. Deterministic text extraction from standard FDR PDFs using pypdf.
2. Provenance tracking: DocumentExtractedFields linked to specific DocumentVersion.
3. Proper handling of scanned/image-only PDFs (OCR_UNAVAILABLE/FAILED without fake data).
4. Partial extraction when documents contain only sparse fields.
5. Malformed/corrupted PDF resilience without 500 crashes.
6. Downstream Module 3 validation engine trigger: cross-validation rules (VAL-XSRC-001)
   detect discrepancies between uploaded FDR evidence and registry values.
7. Multi-version upload and version-specific extraction integrity.
8. Idempotent extraction retry endpoint POST /documents/{id}/versions/{v_id}/extract.
9. P0 Security enforcement: Auditor read-only rejection and institution isolation.
"""
import io
import uuid
from decimal import Decimal
from datetime import date
import pytest
from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.main import app
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.extracted_fields_model import DocumentExtractedFields
from app.modules.validation.models import ValidationFinding
from app.modules.documents.scanner import DemoScannerProvider, DisabledScannerProvider, set_scanner_provider
from app.core.security import create_access_token


@pytest.fixture(autouse=True)
def setup_test_scanner():
    """Configure DemoScannerProvider for extraction test suite."""
    set_scanner_provider(DemoScannerProvider())
    yield
    set_scanner_provider(DisabledScannerProvider())


def _make_fdr_pdf(
    bank_name: str = "State Bank of India",
    ref_no: str = "FDR-SBI-2026-9999",
    amount_str: str = "Rs. 10,00,000.00",
    issue_date_str: str = "15/01/2026",
    maturity_date_str: str = "15/01/2027",
    account_holder: str = "Apex Institute of Technology",
    lien_holder: str = "AICTE Regulation Bureau",
) -> bytes:
    """Generates a real, binary text-based PDF fixture using reportlab."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, bank_name)
    c.drawString(100, 730, f"Fixed Deposit Receipt No: {ref_no}")
    c.drawString(100, 710, f"Deposit Amount: {amount_str}")
    c.drawString(100, 690, f"Issue Date: {issue_date_str}")
    c.drawString(100, 670, f"Maturity Date: {maturity_date_str}")
    c.drawString(100, 650, f"Account Holder: {account_holder}")
    c.drawString(100, 630, f"Lien Marked To: {lien_holder}")
    c.save()
    return buf.getvalue()


def _make_empty_pdf() -> bytes:
    """Generates a valid PDF with no extractable text (simulating image-only/scanned)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def extraction_fixture(db_session: Session):
    """Sets up institutions, users, and instrument."""
    inst1 = Institution(
        code="INST-EXT-01",
        legal_name="Apex Institute of Technology",
        contact_email="director@apex.edu.in",
        state="Maharashtra",
        is_active=True,
    )
    inst2 = Institution(
        code="INST-EXT-02",
        legal_name="Other Institute",
        contact_email="director@other.edu.in",
        state="Delhi",
        is_active=True,
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    user_inst1 = User(
        id=str(uuid.uuid4()),
        full_name="Apex Officer",
        email="officer@apex.edu.in",
        password_hash="mock_hash",
        role="INSTITUTION_USER",
        is_active=True,
        institution_id=inst1.id,
    )
    user_inst2 = User(
        id=str(uuid.uuid4()),
        full_name="Other Officer",
        email="officer@other.edu.in",
        password_hash="mock_hash",
        role="INSTITUTION_USER",
        is_active=True,
        institution_id=inst2.id,
    )
    user_auditor = User(
        id=str(uuid.uuid4()),
        full_name="Compliance Auditor",
        email="auditor@aicte.gov.in",
        password_hash="mock_hash",
        role="AUDITOR",
        is_active=True,
        institution_id=None,
    )
    user_scrutiny = User(
        id=str(uuid.uuid4()),
        full_name="Scrutiny Officer",
        email="scrutiny@aicte.gov.in",
        password_hash="mock_hash",
        role="SCRUTINY_OFFICER",
        is_active=True,
        institution_id=None,
    )
    db_session.add_all([user_inst1, user_inst2, user_auditor, user_scrutiny])
    db_session.flush()

    # Registered Instrument in DB: Amount is Rs 10,00,000
    instrument = Instrument(
        reference_number="FDR-SBI-2026-9999",
        institution_id=inst1.id,
        bank_name="State Bank of India",
        branch="Main Branch",
        amount=Decimal("1000000.00"),
        issue_date=date(2026, 1, 15),
        maturity_date=date(2027, 1, 15),
        status="ACTIVE",
    )
    db_session.add(instrument)
    db_session.commit()

    return {
        "institution1": inst1,
        "institution2": inst2,
        "user_inst1": user_inst1,
        "user_inst2": user_inst2,
        "user_auditor": user_auditor,
        "user_scrutiny": user_scrutiny,
        "instrument": instrument,
    }


def _auth_header(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def test_text_pdf_extraction_success_and_persistence(client: TestClient, db_session: Session, extraction_fixture):
    """
    Upload a genuine text-based FDR PDF.
    Assert extraction runs, populates DocumentExtractedFields, and detail route exposes it.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    pdf_bytes = _make_fdr_pdf()

    files = {"file": ("fdr_receipt.pdf", pdf_bytes, "application/pdf")}
    data = {
        "category": "FDR_COPY",
        "title": "Fixed Deposit Certificate",
        "description": "Original FDR PDF certificate",
    }

    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data,
        files=files,
    )
    assert resp.status_code == 200, resp.text
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["extraction_status"] == "COMPLETED"
    assert res_data["extracted_fields_id"] is not None

    doc_id = res_data["document_id"]
    version_id = res_data["version_id"]

    # Verify DocumentExtractedFields persisted in DB with exact provenance
    ext = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == version_id)
    )
    assert ext is not None
    assert ext.document_id == doc_id
    assert ext.instrument_id == instrument.id
    assert ext.extraction_status == "COMPLETED"
    assert ext.doc_bank_name == "State Bank of India"
    assert ext.doc_reference_number == "FDR-SBI-2026-9999"
    assert ext.doc_amount_str == "1000000.00"
    assert ext.doc_issue_date_str == "2026-01-15"
    assert ext.doc_maturity_date_str == "2027-01-15"
    assert ext.doc_account_holder == "Apex Institute of Technology"
    assert "All India Council for Technical Education" in (ext.doc_lien_holder or "")

    # Verify GET /documents/{id} exposes extracted fields
    detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=_auth_header(user))
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    v1 = detail["versions"][0]
    assert v1["extracted_fields"] is not None
    assert v1["extracted_fields"]["extraction_status"] == "COMPLETED"
    assert v1["extracted_fields"]["doc_amount_str"] == "1000000.00"


def test_scanned_image_only_pdf_records_ocr_unavailable(client: TestClient, db_session: Session, extraction_fixture):
    """
    When an image-only / scanned PDF with no extractable text is uploaded:
    Pipeline marks status as FAILED with an explicit OCR unavailable notice.
    Crucially: NEVER fabricates synthetic values.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    pdf_bytes = _make_empty_pdf()
    files = {"file": ("scanned_fdr.pdf", pdf_bytes, "application/pdf")}
    data = {"category": "FDR_COPY", "title": "Scanned Copy"}

    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data,
        files=files,
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["extraction_status"] == "FAILED"

    version_id = res_data["version_id"]
    ext = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == version_id)
    )
    assert ext is not None
    assert ext.extraction_status == "FAILED"
    assert "OCR text extraction unavailable" in (ext.error_details or "")
    # Check NO fabricated values
    assert ext.doc_bank_name is None
    assert ext.doc_amount_str is None
    assert ext.doc_reference_number is None


def test_partial_extraction_for_sparse_pdf(client: TestClient, db_session: Session, extraction_fixture):
    """
    A PDF with only bank name and certificate number, but without amounts or dates.
    Resulting status must be PARTIAL.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "HDFC Bank")
    c.drawString(100, 730, "Deposit Reference No: HDFC-2026-7777")
    c.save()
    pdf_bytes = buf.getvalue()

    files = {"file": ("sparse_fdr.pdf", pdf_bytes, "application/pdf")}
    data = {"category": "FDR_COPY", "title": "Sparse Document"}

    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data,
        files=files,
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["extraction_status"] == "PARTIAL"

    ext = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == res_data["version_id"])
    )
    assert ext.extraction_status == "PARTIAL"
    assert ext.doc_bank_name == "HDFC Bank"
    assert ext.doc_reference_number == "HDFC-2026-7777"
    assert ext.doc_amount_str is None


def test_corrupted_malformed_pdf_resilience(client: TestClient, db_session: Session, extraction_fixture):
    """
    A corrupt byte stream marked as application/pdf should not trigger an unhandled 500 server crash.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    corrupted_bytes = b"%PDF-1.4\n%corrupted garbage bytes that fail pypdf parsing completely\n%%EOF"
    files = {"file": ("corrupt.pdf", corrupted_bytes, "application/pdf")}
    data = {"category": "FDR_COPY", "title": "Corrupt File"}

    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data,
        files=files,
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["extraction_status"] == "FAILED"

    ext = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == res_data["version_id"])
    )
    assert ext.extraction_status == "FAILED"
    assert ext.error_details is not None


def test_downstream_cross_validation_trigger_discrepancy(client: TestClient, db_session: Session, extraction_fixture):
    """
    Registry Amount is Rs 10,00,000.
    Upload document where printed Amount is Rs 5,00,000.
    Extraction must run, and downstream validation engine rule VAL-XSRC-001 must flag discrepancy!
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]  # amount = 1000000.00

    # Upload document with 5,00,000.00
    pdf_bytes = _make_fdr_pdf(amount_str="Rs. 5,00,000.00")
    files = {"file": ("mismatched_amount.pdf", pdf_bytes, "application/pdf")}
    data = {"category": "FDR_COPY", "title": "Mismatched Amount FDR"}

    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data,
        files=files,
    )
    assert resp.status_code == 200
    assert resp.json()["extraction_status"] == "COMPLETED"

    # Query Module 3 validation findings for this instrument
    findings = list(
        db_session.scalars(
            select(ValidationFinding).where(ValidationFinding.instrument_id == instrument.id)
        ).all()
    )
    rule_codes = [f.rule_id for f in findings]
    assert "VAL-XSRC-001" in rule_codes, f"Expected VAL-XSRC-001 discrepancy finding, got: {rule_codes}"

    amount_finding = next(f for f in findings if f.rule_id == "VAL-XSRC-001")
    finding_text = f"{amount_finding.title} {amount_finding.explanation} {amount_finding.observed_value} {amount_finding.expected_value}"
    assert any(x in finding_text for x in ("1000000", "10,00,000", "500000", "5,00,000", "amount", "mismatch"))


def test_version_provenance_and_version_upload(client: TestClient, db_session: Session, extraction_fixture):
    """
    Uploading a new document version creates a separate DocumentExtractedFields record
    linked to version 2, while preserving version 1 provenance.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    # Version 1 upload (amount = 5,00,000)
    pdf_v1 = _make_fdr_pdf(amount_str="Rs. 5,00,000.00")
    files1 = {"file": ("fdr_v1.pdf", pdf_v1, "application/pdf")}
    data1 = {"category": "FDR_COPY", "title": "FDR Document"}
    resp1 = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data=data1,
        files=files1,
    )
    assert resp1.status_code == 200
    doc_id = resp1.json()["document_id"]
    v1_id = resp1.json()["version_id"]

    # Version 2 upload (corrected amount = 10,00,000)
    pdf_v2 = _make_fdr_pdf(amount_str="Rs. 10,00,000.00")
    files2 = {"file": ("fdr_v2.pdf", pdf_v2, "application/pdf")}
    resp2 = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        headers=_auth_header(user),
        files=files2,
    )
    assert resp2.status_code == 200, resp2.text
    res2_data = resp2.json()
    assert res2_data["version_number"] == 2
    v2_id = res2_data["version_id"]
    assert res2_data["extraction_status"] == "COMPLETED"

    # Verify both versions have separate extraction records
    ext_v1 = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == v1_id)
    )
    ext_v2 = db_session.scalar(
        select(DocumentExtractedFields).where(DocumentExtractedFields.document_version_id == v2_id)
    )
    assert ext_v1 is not None and ext_v2 is not None
    assert ext_v1.id != ext_v2.id
    assert ext_v1.doc_amount_str == "500000.00"
    assert ext_v2.doc_amount_str == "1000000.00"


def test_extraction_retry_endpoint(client: TestClient, db_session: Session, extraction_fixture):
    """
    POST /documents/{doc_id}/versions/{version_id}/extract allows on-demand re-extraction
    and updates existing DocumentExtractedFields in place without primary key duplicate error.
    """
    user = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    pdf_bytes = _make_fdr_pdf()
    files = {"file": ("fdr_orig.pdf", pdf_bytes, "application/pdf")}
    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user),
        data={"category": "FDR_COPY", "title": "Original FDR"},
        files=files,
    )
    doc_id = resp.json()["document_id"]
    v_id = resp.json()["version_id"]

    # Trigger re-extraction
    retry_resp = client.post(
        f"/api/v1/documents/{doc_id}/versions/{v_id}/extract",
        headers=_auth_header(user),
    )
    assert retry_resp.status_code == 200, retry_resp.text
    retry_data = retry_resp.json()
    assert retry_data["extraction_status"] == "COMPLETED"
    assert retry_data["doc_bank_name"] == "State Bank of India"
    assert retry_data["doc_reference_number"] == "FDR-SBI-2026-9999"


def test_p0_auditor_and_cross_tenant_restrictions(client: TestClient, db_session: Session, extraction_fixture):
    """
    Auditor cannot upload or trigger extraction (strictly read-only).
    User from Institution 2 cannot extract or upload documents for Institution 1.
    """
    user_auditor = extraction_fixture["user_auditor"]
    user_inst2 = extraction_fixture["user_inst2"]
    user_inst1 = extraction_fixture["user_inst1"]
    instrument = extraction_fixture["instrument"]

    pdf_bytes = _make_fdr_pdf()

    # 1. Auditor upload denied
    files = {"file": ("fdr.pdf", pdf_bytes, "application/pdf")}
    resp = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user_auditor),
        data={"category": "FDR_COPY", "title": "Audit Test"},
        files=files,
    )
    assert resp.status_code == 403, "Auditor must not be allowed to upload documents"

    # 2. Institution 2 user cannot upload to Institution 1 instrument
    resp_cross = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user_inst2),
        data={"category": "FDR_COPY", "title": "Cross Inst Test"},
        files=files,
    )
    assert resp_cross.status_code == 403, "Cross-tenant document upload must be forbidden"

    # 3. Create document with Institution 1 user
    resp_valid = client.post(
        f"/api/v1/instruments/{instrument.id}/documents",
        headers=_auth_header(user_inst1),
        data={"category": "FDR_COPY", "title": "Valid Doc"},
        files=files,
    )
    doc_id = resp_valid.json()["document_id"]
    version_id = resp_valid.json()["version_id"]

    # 4. Auditor retry extraction denied
    resp_aud_extract = client.post(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/extract",
        headers=_auth_header(user_auditor),
    )
    assert resp_aud_extract.status_code == 403

    # 5. Institution 2 user retry extraction denied
    resp_inst2_extract = client.post(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/extract",
        headers=_auth_header(user_inst2),
    )
    assert resp_inst2_extract.status_code == 403
