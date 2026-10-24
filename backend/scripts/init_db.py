"""
Database Initialization and Seed Script
Populates foundational sample institutions, provisioned users, and FDR instruments for demonstration.
"""
import sys
import os
from datetime import date, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.modules.institutions.models import Institution
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.auth.service import provision_user
from app.modules.audit.service import log_audit_event
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
)


def seed_database():
    print("[FDR Sentinel] Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_inst = db.query(Institution).first()
        if existing_inst:
            print("[FDR Sentinel] Database already contains records. Skipping duplicate seeding.")
            return

        print("[FDR Sentinel] Seeding sample institutions...")
        inst1 = Institution(
            code="1-10924811",
            legal_name="Delhi Institute of Engineering and Technology",
            display_name="DIET Delhi",
            institution_type="TECHNICAL_INSTITUTE",
            contact_name="Dr. R. K. Sharma (Registrar)",
            contact_email="registrar@diet-delhi.ac.in",
            contact_phone="+91-11-23891000",
            address_line1="Sector 14, Dwarka Institutional Area",
            city="New Delhi",
            state="Delhi",
            postal_code="110078",
            is_active=True,
            is_synthetic=True,
        )
        inst2 = Institution(
            code="1-20491823",
            legal_name="Maharashtra State Institute of Management Studies",
            display_name="MSIMS Pune",
            institution_type="MANAGEMENT_INSTITUTE",
            contact_name="Prof. S. Patil (Director)",
            contact_email="nodal@msim-pune.edu.in",
            contact_phone="+91-20-25678000",
            address_line1="Shivajinagar Campus, Ganeshkhind Road",
            city="Pune",
            state="Maharashtra",
            postal_code="411005",
            is_active=True,
            is_synthetic=True,
        )
        inst3 = Institution(
            code="1-30918274",
            legal_name="Karnataka Academy of Pharmaceutical Sciences",
            display_name="KAPS Bengaluru",
            institution_type="PHARMACY_COLLEGE",
            contact_name="Dr. V. Rao (Dean)",
            contact_email="admin@kaps-blr.ac.in",
            contact_phone="+91-80-22961000",
            address_line1="Rajajinagar 2nd Block",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560010",
            is_active=True,
            is_synthetic=True,
        )
        db.add_all([inst1, inst2, inst3])
        db.commit()
        db.refresh(inst1)
        db.refresh(inst2)
        db.refresh(inst3)

        print("[FDR Sentinel] Seeding provisioned demo accounts...")
        # 1. System Administrator
        try:
            admin = provision_user(
                db=db,
                full_name="AICTE Regulation Administrator",
                email="admin@aicte-india.org",
                password="AdminPassword@2026",
                role=ROLE_SYSTEM_ADMIN,
                institution_id=None,
                must_change_password=False,
                actor_email="SYSTEM_INIT",
                actor_role="SYSTEM",
            )
        except ConflictException:
            print("  - Admin user already exists, skipping.")

        # 2. Scrutiny Officer
        try:
            officer = provision_user(
                db=db,
                full_name="Officer Ramesh Verma",
                email="scrutiny.verma@aicte-india.org",
                password="OfficerPassword@2026",
                role=ROLE_SCRUTINY_OFFICER,
                institution_id=None,
                must_change_password=False,
                actor_email="SYSTEM_INIT",
                actor_role="SYSTEM",
            )
        except ConflictException:
            print("  - Scrutiny officer already exists, skipping.")

        # 3. Institution User (DIET Delhi)
        try:
            inst_user = provision_user(
                db=db,
                full_name="DIET Nodal Officer",
                email="nodal@diet-delhi.ac.in",
                password="NodalPassword@2026",
                role=ROLE_INSTITUTION_USER,
                institution_id=inst1.id,
                must_change_password=True,  # Needs password rotation on first login
                actor_email="SYSTEM_INIT",
                actor_role="SYSTEM",
            )
        except ConflictException:
            print("  - Institution user already exists, skipping.")

        # 4. Auditor
        try:
            auditor = provision_user(
                db=db,
                full_name="Auditor Sunita Deshmukh",
                email="auditor.compliance@aicte-india.org",
                password="AuditorPassword@2026",
                role=ROLE_AUDITOR,
                institution_id=None,
                must_change_password=False,
                actor_email="SYSTEM_INIT",
                actor_role="SYSTEM",
            )
        except ConflictException:
            print("  - Auditor user already exists, skipping.")

        print("[FDR Sentinel] Seeding sample FDR instruments...")
        today = date.today()
        fdr1 = Instrument(
            institution_id=inst1.id,
            reference_number="FDR-SBI-2024-88091",
            bank_name="State Bank of India",
            branch="Connaught Place, New Delhi",
            amount=3500000.00,
            currency="INR",
            issue_date=today - timedelta(days=365 * 2),
            maturity_date=today + timedelta(days=365 * 3),
            status="VERIFIED",
            verification_level="L3_OFFICER_VERIFIED",
            joint_with_aicte=True,
            lien_marked=True,
            remarks="Verified joint FDR for permanent campus approval.",
        )
        fdr2 = Instrument(
            institution_id=inst2.id,
            reference_number="FDR-HDFC-2026-11029",
            bank_name="HDFC Bank",
            branch="FC Road, Pune",
            amount=2500000.00,
            currency="INR",
            issue_date=today - timedelta(days=60),
            maturity_date=today + timedelta(days=45),  # Expiring soon (<90 days)
            status="ACTIVE",
            verification_level="L4_BANK_CONFIRMED",
            joint_with_aicte=True,
            lien_marked=True,
            remarks="Bank confirmation letter received directly via branch nodals.",
        )
        fdr3 = Instrument(
            institution_id=inst3.id,
            reference_number="FDR-PNB-2026-99381",
            bank_name="Punjab National Bank",
            branch="MG Road, Bengaluru",
            amount=1500000.00,
            currency="INR",
            issue_date=today - timedelta(days=10),
            maturity_date=today + timedelta(days=365 * 5),
            status="UNDER_SCRUTINY",
            verification_level="L1_DECLARED",
            joint_with_aicte=True,
            lien_marked=False,
            remarks="Awaiting lien confirmation letter from issuing bank branch.",
        )
        db.add_all([fdr1, fdr2, fdr3])
        db.commit()

        print("[FDR Sentinel] Seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
