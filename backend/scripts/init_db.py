"""
Database Initialization and Seed Script
Populates initial sample institutions and FDR instruments for demonstration.
"""
import sys
import os
from datetime import date, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.audit.service import log_audit_event


def seed_database():
    print("[FDR Sentinel] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Institution).first()
        if existing:
            print("[FDR Sentinel] Database already contains records. Skipping seed.")
            return

        print("[FDR Sentinel] Seeding sample institutions...")
        inst1 = Institution(
            aicte_id="1-10924811",
            name="Delhi Institute of Engineering and Technology",
            state="Delhi",
            category="Engineering & Technology",
            contact_email="registrar@diet-delhi.ac.in",
            status="ACTIVE",
        )
        inst2 = Institution(
            aicte_id="1-20491823",
            name="Maharashtra State Institute of Management",
            state="Maharashtra",
            category="Management",
            contact_email="nodal@msim-pune.edu.in",
            status="ACTIVE",
        )
        inst3 = Institution(
            aicte_id="1-30918274",
            name="Karnataka Academy of Pharmaceutical Sciences",
            state="Karnataka",
            category="Pharmacy",
            contact_email="admin@kaps-blr.ac.in",
            status="ACTIVE",
        )
        db.add_all([inst1, inst2, inst3])
        db.commit()
        db.refresh(inst1)
        db.refresh(inst2)
        db.refresh(inst3)

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
        db.refresh(fdr1)
        db.refresh(fdr2)
        db.refresh(fdr3)

        print("[FDR Sentinel] Seeding initial audit events...")
        log_audit_event(
            db=db,
            entity_type="instrument",
            entity_id=fdr1.id,
            action="FDR_VERIFIED",
            actor_email="officer.verma@aicte-india.org",
            actor_role="scrutiny_officer",
            details="Verified joint FDR deposit against physical and bank verification records.",
            ip_address="10.0.4.12",
        )
        log_audit_event(
            db=db,
            entity_type="instrument",
            entity_id=fdr2.id,
            action="BANK_CONFIRMED",
            actor_email="bank.nodal@hdfcbank.com",
            actor_role="bank_api",
            details="Simulated API bank confirmation token validated (Level 4 evidence).",
            ip_address="192.168.1.100",
        )
        log_audit_event(
            db=db,
            entity_type="instrument",
            entity_id=fdr3.id,
            action="FDR_SUBMISSION",
            actor_email="admin@kaps-blr.ac.in",
            actor_role="institution_user",
            details="New FDR instrument submitted for pharmacy intake extension.",
            ip_address="115.240.82.11",
        )

        print("[FDR Sentinel] Seed completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
