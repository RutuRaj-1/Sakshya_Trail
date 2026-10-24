"""
Health and Readiness Endpoints
Provides system observability and PostgreSQL/database connectivity probes.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.common.schemas import HealthResponse, ReadinessResponse
from app.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["System Health & Diagnostics"])


@router.get("/live", response_model=HealthResponse, summary="Liveness Probe")
def liveness_check():
    """
    Kubernetes / system liveness check.
    Confirms the FastAPI worker process is active and receiving requests.
    """
    return HealthResponse(
        status="alive",
        timestamp=datetime.now(timezone.utc),
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness Probe")
def readiness_check():
    """
    Readiness check reporting whether PostgreSQL / database layer is reachable.
    Executes a database ping ('SELECT 1') and returns components status.
    """
    db_result = check_database_connection()
    is_ready = db_result["is_ready"]
    overall_status = "ready" if is_ready else "degraded"

    body = ReadinessResponse(
        status=overall_status,
        is_ready=is_ready,
        timestamp=datetime.now(timezone.utc),
        components={
            "database": db_result,
            "api": {
                "status": "operational",
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
            },
        },
    )

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))
