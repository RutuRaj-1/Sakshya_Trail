"""
FDR Sentinel - AICTE Security Deposit / FDR Lifecycle Integrity Platform
FastAPI Application Entrypoint
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
# Import all models to ensure metadata registration
import app.modules.auth.models
import app.modules.institutions.models
import app.modules.instruments.models
import app.modules.audit.models
import app.modules.documents.models
import app.modules.validation.models
import app.modules.validation.extracted_fields_model
import app.modules.verification.models
import app.modules.lifecycle.models

from app.api.v1.router import api_v1_router
from app.api.v1.endpoints.health import liveness_check, readiness_check
from app.common.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist for local development / testing
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[Startup Warning] Could not automatically create tables: {exc}")
    yield
    # Shutdown logic if any
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AICTE Security Deposit and Fixed Deposit Receipt (FDR) Lifecycle Integrity "
        "and Governance Platform API."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^http:\/\/(localhost|127\.0\.0\.1)(:[0-9]+)?$" if settings.DEBUG else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include Versioned API Routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Top-level health probe aliases for orchestrator compatibility
app.add_api_route("/healthz", liveness_check, methods=["GET"], tags=["Root Health"])
app.add_api_route("/readyz", readiness_check, methods=["GET"], tags=["Root Health"])


@app.get("/", tags=["Root"])
def root_info():
    """Service welcome information and navigation links."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": {
            "liveness": f"{settings.API_V1_STR}/health/live",
            "readiness": f"{settings.API_V1_STR}/health/ready",
        },
    }
