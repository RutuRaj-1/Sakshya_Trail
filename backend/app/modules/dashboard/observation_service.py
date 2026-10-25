"""
Scrutiny Observation Service (Module 7 — Command Center)
Implements PRD-FR-072 & PRD-FR-073:
Append-only scrutiny observations, non-destructive supersession chains,
audit trail logging, and tenant isolation.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.release.models import ReleaseRequest
from app.modules.audit.service import log_audit_event
from app.modules.dashboard.models import ScrutinyObservation
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions


class ScrutinyObservationService:
    """Manages append-only observations with supersession history."""

    @staticmethod
    def create_observation(
        db: Session,
        current_user: User,
        instrument_id: Optional[str] = None,
        release_request_id: Optional[str] = None,
        observation_text: str = "",
        observation_category: str = "GENERAL",
        finding_id: Optional[str] = None,
        supporting_document_id: Optional[str] = None,
        supporting_version_number: Optional[int] = None,
        is_internal_only: bool = False,
    ) -> ScrutinyObservation:
        """
        Records a new scrutiny observation with strict authorship and timestamping.
        """
        # Read-only check for auditors
        if current_user.role == "AUDITOR":
            raise AppException(
                "Auditors possess read-only permissions and cannot create scrutiny observations.",
                status_code=403,
                code="AUDITOR_READ_ONLY",
            )

        if not observation_text or not observation_text.strip():
            raise AppException("Observation text cannot be blank.", status_code=422, code="BLANK_OBSERVATION")

        if not instrument_id and not release_request_id:
            raise AppException(
                "Observation must be linked to either an instrument or a release request.",
                status_code=422,
                code="MISSING_TARGET_ENTITY",
            )

        # Enforce scope on target entity
        if instrument_id:
            conditions = enforce_scope_and_get_conditions(current_user=current_user, db=db)
            inst = db.scalars(select(Instrument).where(*conditions, Instrument.id == instrument_id)).first()
            if not inst:
                raise AppException("Instrument not found or unauthorized", status_code=404, code="RECORD_NOT_FOUND")

        if release_request_id:
            rel = db.get(ReleaseRequest, release_request_id)
            if not rel:
                raise AppException("Release request not found", status_code=404, code="RECORD_NOT_FOUND")
            if current_user.role == "INSTITUTION_USER" and rel.institution_id != current_user.institution_id:
                raise AppException("Cross-institution access denied", status_code=403, code="TENANT_ISOLATION_ERROR")

        # Institution users cannot create internal-only notes
        effective_internal = is_internal_only
        if current_user.role == "INSTITUTION_USER":
            effective_internal = False

        obs = ScrutinyObservation(
            instrument_id=instrument_id,
            release_request_id=release_request_id,
            finding_id=finding_id,
            supporting_document_id=supporting_document_id,
            supporting_version_number=supporting_version_number,
            observation_category=observation_category.upper().strip(),
            observation_text=observation_text.strip(),
            author_user_id=current_user.id,
            author_role=current_user.role,
            status="RECORDED",
            is_internal_only=effective_internal,
        )
        db.add(obs)
        db.flush()

        # Audit event
        log_audit_event(
            db=db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            actor_email=current_user.email,
            action="SCRUTINY_OBSERVATION_CREATED",
            entity_type="SCRUTINY_OBSERVATION",
            entity_id=obs.id,
            metadata={
                "instrument_id": instrument_id,
                "release_request_id": release_request_id,
                "category": obs.observation_category,
                "is_internal_only": obs.is_internal_only,
            },
        )
        db.commit()
        db.refresh(obs)
        return obs

    @staticmethod
    def amend_observation(
        db: Session,
        current_user: User,
        observation_id: str,
        observation_text: str,
        amendment_reason: str,
        is_internal_only: Optional[bool] = None,
    ) -> ScrutinyObservation:
        """
        Creates an amendment / superseding observation while preserving the original note intact.
        """
        if current_user.role == "AUDITOR":
            raise AppException("Auditors possess read-only permissions.", status_code=403, code="AUDITOR_READ_ONLY")

        if not observation_text or not observation_text.strip():
            raise AppException("Updated observation text cannot be blank.", status_code=422, code="BLANK_OBSERVATION")
        if not amendment_reason or not amendment_reason.strip():
            raise AppException("Amendment reason is required.", status_code=422, code="BLANK_REASON")

        prior_obs = db.get(ScrutinyObservation, observation_id)
        if not prior_obs:
            raise AppException("Observation not found", status_code=404, code="RECORD_NOT_FOUND")

        # Authorship or officer authority check
        is_author = prior_obs.author_user_id == current_user.id
        is_elevated_role = current_user.role in ["SCRUTINY_OFFICER", "BRANCH_HEAD", "COMPETENT_AUTHORITY", "SYSTEM_ADMIN"]
        if not (is_author or is_elevated_role):
            raise AppException("Unauthorized to amend this scrutiny observation", status_code=403, code="PERMISSION_DENIED")

        # Check tenant isolation
        if current_user.role == "INSTITUTION_USER":
            conditions = enforce_scope_and_get_conditions(current_user=current_user, db=db)
            inst = db.scalars(select(Instrument).where(*conditions, Instrument.id == prior_obs.instrument_id)).first()
            if not inst:
                raise AppException("Access denied to target instrument", status_code=403, code="TENANT_ISOLATION_ERROR")

        now = datetime.now(timezone.utc)

        # Create superseding observation
        effective_internal = prior_obs.is_internal_only if is_internal_only is None else is_internal_only
        if current_user.role == "INSTITUTION_USER":
            effective_internal = False

        amended_obs = ScrutinyObservation(
            instrument_id=prior_obs.instrument_id,
            release_request_id=prior_obs.release_request_id,
            finding_id=prior_obs.finding_id,
            supporting_document_id=prior_obs.supporting_document_id,
            supporting_version_number=prior_obs.supporting_version_number,
            observation_category=prior_obs.observation_category,
            observation_text=observation_text.strip(),
            author_user_id=current_user.id,
            author_role=current_user.role,
            status="AMENDED",
            supersedes_id=prior_obs.id,
            is_internal_only=effective_internal,
        )
        db.add(amended_obs)
        db.flush()

        # Update prior observation to SUPERSEDED without deleting content
        prior_obs.status = "SUPERSEDED"
        prior_obs.superseded_by_id = amended_obs.id
        prior_obs.updated_at = now

        log_audit_event(
            db=db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            actor_email=current_user.email,
            action="SCRUTINY_OBSERVATION_AMENDED",
            entity_type="SCRUTINY_OBSERVATION",
            entity_id=amended_obs.id,
            metadata={
                "supersedes_id": prior_obs.id,
                "amendment_reason": amendment_reason.strip(),
            },
        )
        db.commit()
        db.refresh(amended_obs)
        return amended_obs

    @staticmethod
    def resolve_observation(
        db: Session,
        current_user: User,
        observation_id: str,
        resolution_reason: str,
    ) -> ScrutinyObservation:
        """
        Marks an observation as resolved with mandatory rationale.
        """
        if current_user.role == "AUDITOR":
            raise AppException("Auditors possess read-only permissions.", status_code=403, code="AUDITOR_READ_ONLY")

        if not resolution_reason or not resolution_reason.strip():
            raise AppException("Resolution reason cannot be blank.", status_code=422, code="BLANK_REASON")

        # Resolving observations requires scrutiny officer or elevated role
        if current_user.role not in ["SCRUTINY_OFFICER", "BRANCH_HEAD", "COMPETENT_AUTHORITY", "SYSTEM_ADMIN"]:
            raise AppException(
                "Only scrutiny officers, branch heads, or system administrators can resolve observations.",
                status_code=403,
                code="PERMISSION_DENIED",
            )

        obs = db.get(ScrutinyObservation, observation_id)
        if not obs:
            raise AppException("Observation not found", status_code=404, code="RECORD_NOT_FOUND")

        now = datetime.now(timezone.utc)
        obs.status = "RESOLVED"
        obs.resolution_reason = resolution_reason.strip()
        obs.resolved_at = now
        obs.resolved_by_user_id = current_user.id
        obs.updated_at = now

        log_audit_event(
            db=db,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            actor_email=current_user.email,
            action="SCRUTINY_OBSERVATION_RESOLVED",
            entity_type="SCRUTINY_OBSERVATION",
            entity_id=obs.id,
            metadata={
                "resolution_reason": obs.resolution_reason,
            },
        )
        db.commit()
        db.refresh(obs)
        return obs

    @staticmethod
    def get_observations(
        db: Session,
        current_user: User,
        instrument_id: Optional[str] = None,
        release_request_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns all observations for an instrument or release case, respecting internal-only secrecy.
        """
        if instrument_id:
            conditions = enforce_scope_and_get_conditions(current_user=current_user, db=db)
            inst = db.scalars(select(Instrument).where(*conditions, Instrument.id == instrument_id)).first()
            if not inst:
                raise AppException("Instrument not found or unauthorized", status_code=404, code="RECORD_NOT_FOUND")

        stmt = select(ScrutinyObservation)
        if instrument_id:
            stmt = stmt.where(ScrutinyObservation.instrument_id == instrument_id)
        if release_request_id:
            stmt = stmt.where(ScrutinyObservation.release_request_id == release_request_id)

        # Hide internal-only notes from institution users
        if current_user.role == "INSTITUTION_USER":
            stmt = stmt.where(ScrutinyObservation.is_internal_only.is_(False))

        stmt = stmt.order_by(ScrutinyObservation.created_at.asc())
        records = db.scalars(stmt).all()

        results = []
        for o in records:
            results.append({
                "id": o.id,
                "instrument_id": o.instrument_id,
                "release_request_id": o.release_request_id,
                "finding_id": o.finding_id,
                "supporting_document_id": o.supporting_document_id,
                "supporting_version_number": o.supporting_version_number,
                "observation_category": o.observation_category,
                "observation_text": o.observation_text,
                "author_user_id": o.author_user_id,
                "author_name": o.author.full_name if o.author else o.author_user_id,
                "author_role": o.author_role,
                "status": o.status,
                "resolution_reason": o.resolution_reason,
                "resolved_at": o.resolved_at.isoformat() if o.resolved_at else None,
                "resolved_by_user_id": o.resolved_by_user_id,
                "resolved_by_name": o.resolver.full_name if o.resolver else None,
                "supersedes_id": o.supersedes_id,
                "superseded_by_id": o.superseded_by_id,
                "is_internal_only": o.is_internal_only,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            })
        return results
