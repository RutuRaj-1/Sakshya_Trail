"""
CLI Management Script to Bootstrap the Initial System Administrator Safely
Usage:
  python scripts/bootstrap_admin.py --email admin@aicte-india.org --name "AICTE Master Admin"
(Prompts securely for password if not provided via --password or FDR_ADMIN_PASSWORD env var)
"""
import sys
import os
import argparse
import getpass

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.modules.auth.service import provision_user
from app.core.security import ROLE_SYSTEM_ADMIN
from app.common.exceptions import ConflictException, AppException


def main():
    parser = argparse.ArgumentParser(description="Bootstrap the initial SYSTEM_ADMIN user.")
    parser.add_argument("--name", default="AICTE System Administrator", help="Full legal name of the administrator")
    parser.add_argument("--email", required=True, help="Official normalized email address")
    parser.add_argument("--password", help="Password (if omitted, will prompt securely)")
    args = parser.parse_args()

    email = args.email.strip()
    name = args.name.strip()

    # Retrieve password securely
    password = args.password or os.environ.get("FDR_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Enter secure administrator password (min 8 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("[Error] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("[Error] Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin_user = provision_user(
            db=db,
            full_name=name,
            email=email,
            password=password,
            role=ROLE_SYSTEM_ADMIN,
            institution_id=None,
            must_change_password=False,
            actor_email="CLI_BOOTSTRAP",
            actor_role="SYSTEM_ADMIN",
        )
        print(f"[Success] Initial SYSTEM_ADMIN '{admin_user.email}' (ID: {admin_user.id}) created successfully.")
    except ConflictException:
        print(f"[Refused] An account with email '{email}' already exists. Duplicate administrator creation denied.", file=sys.stderr)
        sys.exit(2)
    except AppException as err:
        print(f"[Error] Failed to provision administrator: {err.message}", file=sys.stderr)
        sys.exit(3)
    finally:
        db.close()


if __name__ == "__main__":
    main()
