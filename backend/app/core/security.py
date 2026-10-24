"""
Security and authentication utilities placeholder for Module 1.
"""
from typing import Optional
from datetime import datetime, timezone, timedelta

# Role definitions as specified in PRD §14:
# Role-based access: AICTE Administrator, Scrutiny Officer, Institution Representative, Auditor, Read-Only Observer
ROLE_AICTE_ADMIN = "aicte_admin"
ROLE_SCRUTINY_OFFICER = "scrutiny_officer"
ROLE_INSTITUTION_USER = "institution_user"
ROLE_AUDITOR = "auditor"
ROLE_VIEWER = "viewer"

AVAILABLE_ROLES = [
    ROLE_AICTE_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_VIEWER,
]
