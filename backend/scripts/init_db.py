"""
Database Initialization and Synthetic Demo Data Seeding Script
Safely populates idempotent fictional sample institutions, users across roles,
and FDR instruments in various registry states (including an intentional duplicate for testing).

All synthetic records are clearly marked with `[SYNTHETIC DEMO]` in legal names,
codes, and `is_synthetic=True` flags for regulatory compliance and audit distinction.
"""
import sys
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.modules.institutions.models import Institution
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.auth.service import provision_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_BRANCH_HEAD,
)
from app.common.exceptions import ConflictException


def seed_database(db: Optional[Session] = None):
    """
    Idempotent seeding routine that creates synthetic demo data without duplicate accumulation.
    """
    print("[FDR Sentinel] Ensuring database schema and tables exist...")
    Base.metadata.create_all(bind=engine)

    manage_session = False
    if db is None:
        db = SessionLocal()
        manage_session = True

    try:
        print("[FDR Sentinel] Seeding synthetic demonstration institutions...")
        
        # Institution 1: Active Technical Institute
        inst1 = db.query(Institution).filter(Institution.code == "DEMO-AICTE-001").first()
        if not inst1:
            inst1 = Institution(
                code="DEMO-AICTE-001",
                legal_name="Delhi Institute of Engineering and Technology [SYNTHETIC DEMO]",
                display_name="DIET Delhi (Demo)",
                institution_type="TECHNICAL_INSTITUTE",
                contact_name="Dr. R. K. Sharma (Registrar)",
                contact_email="registrar@diet-delhi.ac.in",
                contact_phone="+91-11-23891000",
                address_line1="Sector 14, Dwarka Institutional Area",
                city="New Delhi",
                state="Delhi",
                postal_code="110078",
                assigned_office="Northern Regional Office",
                is_active=True,
                is_synthetic=True,
            )
            db.add(inst1)
            db.commit()
            db.refresh(inst1)
            print("  + Created synthetic institution: DEMO-AICTE-001 (DIET Delhi)")
        else:
            print("  . Synthetic institution DEMO-AICTE-001 already exists, skipping.")

        # Institution 2: Active Management Institute (For tenant isolation testing)
        inst2 = db.query(Institution).filter(Institution.code == "DEMO-AICTE-002").first()
        if not inst2:
            inst2 = Institution(
                code="DEMO-AICTE-002",
                legal_name="Maharashtra Institute of Management Studies [SYNTHETIC DEMO]",
                display_name="MIMS Pune (Demo)",
                institution_type="MANAGEMENT_INSTITUTE",
                contact_name="Prof. S. Patil (Director)",
                contact_email="nodal@mims-pune.edu.in",
                contact_phone="+91-20-25678000",
                address_line1="Shivajinagar Campus, Ganeshkhind Road",
                city="Pune",
                state="Maharashtra",
                postal_code="411005",
                assigned_office="Western Regional Office",
                is_active=True,
                is_synthetic=True,
            )
            db.add(inst2)
            db.commit()
            db.refresh(inst2)
            print("  + Created synthetic institution: DEMO-AICTE-002 (MIMS Pune)")
        else:
            print("  . Synthetic institution DEMO-AICTE-002 already exists, skipping.")

        # Institution 3: Historical / Inactive Pharmacy College
        inst3 = db.query(Institution).filter(Institution.code == "DEMO-AICTE-003").first()
        if not inst3:
            inst3 = Institution(
                code="DEMO-AICTE-003",
                legal_name="Karnataka Academy of Pharmaceutical Sciences [SYNTHETIC DEMO]",
                display_name="KAPS Bengaluru (Historical)",
                institution_type="PHARMACY_COLLEGE",
                contact_name="Dr. V. Rao (Dean)",
                contact_email="admin@kaps-blr.ac.in",
                contact_phone="+91-80-22961000",
                address_line1="Rajajinagar 2nd Block",
                city="Bengaluru",
                state="Karnataka",
                postal_code="560010",
                assigned_office="South Western Regional Office",
                is_active=False,  # Intentionally inactive to test historical state & deactivation filtering
                is_synthetic=True,
            )
            db.add(inst3)
            db.commit()
            db.refresh(inst3)
            print("  + Created synthetic institution: DEMO-AICTE-003 (KAPS Bengaluru - Inactive)")
        else:
            print("  . Synthetic institution DEMO-AICTE-003 already exists, skipping.")

        print("[FDR Sentinel] Seeding synthetic demonstration users across roles...")
        
        # 1. System Administrator
        try:
            admin = provision_user(
                db=db,
                full_name="AICTE Regulation Administrator [DEMO]",
                email="admin@aicte-india.org",
                password="AdminPassword@2026",
                role=ROLE_SYSTEM_ADMIN,
                institution_id=None,
                must_change_password=False,
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: admin@aicte-india.org (SYSTEM_ADMIN)")
        except ConflictException:
            print("  . User admin@aicte-india.org already exists, skipping.")

        # 2. Scrutiny Officer
        try:
            officer = provision_user(
                db=db,
                full_name="Officer Ramesh Verma [DEMO]",
                email="scrutiny.verma@aicte-india.org",
                password="OfficerPassword@2026",
                role=ROLE_SCRUTINY_OFFICER,
                institution_id=None,
                must_change_password=False,
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: scrutiny.verma@aicte-india.org (SCRUTINY_OFFICER)")
        except ConflictException:
            print("  . User scrutiny.verma@aicte-india.org already exists, skipping.")

        # 3. Branch Head
        try:
            branch_head = provision_user(
                db=db,
                full_name="Dr. Anita Desai [DEMO]",
                email="branch.head.north@aicte-india.org",
                password="BranchPassword@2026",
                role=ROLE_BRANCH_HEAD,
                institution_id=None,
                must_change_password=False,
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: branch.head.north@aicte-india.org (BRANCH_HEAD)")
        except ConflictException:
            print("  . User branch.head.north@aicte-india.org already exists, skipping.")

        # 4. Institution User 1 (DIET Delhi)
        try:
            inst_user_1 = provision_user(
                db=db,
                full_name="DIET Nodal Officer [DEMO]",
                email="nodal@diet-delhi.ac.in",
                password="NodalPassword@2026",
                role=ROLE_INSTITUTION_USER,
                institution_id=inst1.id,
                must_change_password=True,  # Test password rotation on first login
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: nodal@diet-delhi.ac.in (INSTITUTION_USER -> DIET Delhi)")
        except ConflictException:
            print("  . User nodal@diet-delhi.ac.in already exists, skipping.")

        # 5. Institution User 2 (MIMS Pune) - For Tenant Isolation Verification
        try:
            inst_user_2 = provision_user(
                db=db,
                full_name="MIMS Pune Representative [DEMO]",
                email="nodal.pune@mims-demo.ac.in",
                password="NodalPassword@2026",
                role=ROLE_INSTITUTION_USER,
                institution_id=inst2.id,
                must_change_password=False,
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: nodal.pune@mims-demo.ac.in (INSTITUTION_USER -> MIMS Pune)")
        except ConflictException:
            print("  . User nodal.pune@mims-demo.ac.in already exists, skipping.")

        # 6. Compliance Auditor (Read-Only)
        try:
            auditor = provision_user(
                db=db,
                full_name="Auditor Sunita Deshmukh [DEMO]",
                email="auditor.compliance@aicte-india.org",
                password="AuditorPassword@2026",
                role=ROLE_AUDITOR,
                institution_id=None,
                must_change_password=False,
                actor_email="SYNTHETIC_INIT",
                actor_role="SYSTEM_ADMIN",
            )
            print("  + Provisioned: auditor.compliance@aicte-india.org (AUDITOR)")
        except ConflictException:
            print("  . User auditor.compliance@aicte-india.org already exists, skipping.")

        print("[FDR Sentinel] Seeding synthetic demonstration FDR instruments...")
        today = date.today()

        def seed_instrument_if_missing(data: dict):
            existing = db.query(Instrument).filter(
                Instrument.reference_number == data["reference_number"],
                Instrument.bank_name == data["bank_name"],
                Instrument.institution_id == data["institution_id"],
            ).first()
            if not existing:
                instru = Instrument(**data)
                db.add(instru)
                db.commit()
                print(f"  + Seeded instrument: {data['reference_number']} ({data['bank_name']})")
            else:
                print(f"  . Instrument {data['reference_number']} already exists, skipping.")

        # 1. Active Registered FDR (Institution 1)
        seed_instrument_if_missing({
            "institution_id": inst1.id,
            "instrument_type": "FDR",
            "reference_number": "DEMO-FDR-SBI-2024-88091",
            "bank_name": "State Bank of India",
            "branch": "Connaught Place, New Delhi",
            "amount": Decimal("3500000.00"),
            "currency": "INR",
            "issue_date": today - timedelta(days=365 * 2),
            "maturity_date": today + timedelta(days=365 * 3),
            "status": "REGISTERED",
            "trust_level": "L0_DECLARED",
            "lien_holder": "AICTE Regulation Bureau",
            "lien_details": "Verified joint security deposit for technical institute approval.",
            "assigned_office": "Northern Regional Office",
            "is_synthetic": True,
        })

        # 2. Expiring Soon (<90 days) FDR (Institution 2)
        seed_instrument_if_missing({
            "institution_id": inst2.id,
            "instrument_type": "FDR",
            "reference_number": "DEMO-FDR-HDFC-2026-11029",
            "bank_name": "HDFC Bank",
            "branch": "FC Road, Pune",
            "amount": Decimal("2500000.00"),
            "currency": "INR",
            "issue_date": today - timedelta(days=60),
            "maturity_date": today + timedelta(days=45),  # 45 days remaining (<90 days)
            "status": "REGISTERED",
            "trust_level": "L0_DECLARED",
            "lien_holder": "AICTE Regulation Bureau",
            "lien_details": "Security deposit under 90-day renewal notice window.",
            "assigned_office": "Western Regional Office",
            "is_synthetic": True,
        })

        # 3. Draft FDR (Institution 1)
        seed_instrument_if_missing({
            "institution_id": inst1.id,
            "instrument_type": "FDR",
            "reference_number": "DEMO-FDR-PNB-2026-99381",
            "bank_name": "Punjab National Bank",
            "branch": "Dwarka Sector 10, New Delhi",
            "amount": Decimal("1500000.00"),
            "currency": "INR",
            "issue_date": today - timedelta(days=10),
            "maturity_date": today + timedelta(days=365 * 5),
            "status": "DRAFT",
            "trust_level": "L0_DECLARED",
            "lien_holder": "AICTE Regulation Bureau",
            "lien_details": "Draft initial deposit pending institutional board signature.",
            "assigned_office": "Northern Regional Office",
            "is_synthetic": True,
        })

        # 4. Intentionally Duplicated FDR Reference (for testing duplicate-warning path)
        # Record A: Under Institution 1
        seed_instrument_if_missing({
            "institution_id": inst1.id,
            "instrument_type": "FDR",
            "reference_number": "DEMO-FDR-DUP-TEST-99",
            "bank_name": "Canara Bank",
            "branch": "Kashmere Gate, Delhi",
            "amount": Decimal("2000000.00"),
            "currency": "INR",
            "issue_date": today - timedelta(days=180),
            "maturity_date": today + timedelta(days=365 * 2),
            "status": "REGISTERED",
            "trust_level": "L0_DECLARED",
            "lien_holder": "AICTE Regulation Bureau",
            "lien_details": "Baseline instrument for duplicate reference number testing.",
            "assigned_office": "Northern Regional Office",
            "is_synthetic": True,
        })

        # Record B: Intentionally recorded matching Bank and Reference under Institution 2
        # (Demonstrating that duplicate warnings allow independent review without silent merging)
        seed_instrument_if_missing({
            "institution_id": inst2.id,
            "instrument_type": "FDR",
            "reference_number": "DEMO-FDR-DUP-TEST-99",
            "bank_name": "Canara Bank",
            "branch": "Shivajinagar, Pune",
            "amount": Decimal("2000000.00"),
            "currency": "INR",
            "issue_date": today - timedelta(days=30),
            "maturity_date": today + timedelta(days=365 * 3),
            "status": "REGISTERED",
            "trust_level": "L0_DECLARED",
            "lien_holder": "AICTE Regulation Bureau",
            "lien_details": "Potential duplicate record intentionally confirmed for regulatory audit review.",
            "assigned_office": "Western Regional Office",
            "is_synthetic": True,
        })

        print("[FDR Sentinel] Synthetic demo seeding completed successfully!")
    finally:
        if manage_session:
            db.close()


if __name__ == "__main__":
    seed_database()
