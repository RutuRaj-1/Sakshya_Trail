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
import app.modules.release.models

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
        from app.db.session import SessionLocal
        from app.modules.documents.service import DocumentService
        with SessionLocal() as db:
            DocumentService.initialize_default_categories(db)
            from app.modules.auth.models import User
            if db.query(User).count() == 0:
                print("[Startup INFO] Empty database detected. Auto-seeding initial users & demo dataset...")
                try:
                    from scripts.init_db import seed_database
                    seed_database(db)
                    print("[Startup INFO] Initial dataset seeded successfully.")
                except Exception as seed_err:
                    print(f"[Startup Warning] Auto-seeding encountered: {seed_err}")
    except Exception as exc:
        print(f"[Startup Warning] Could not automatically initialize database: {exc}")

    # Startup: Validate and initialise document storage backend
    try:
        from app.modules.documents.storage import get_storage_provider
        get_storage_provider()  # logs its backend choice
        if settings.FIREBASE_STORAGE_ENABLED and settings.DOCUMENT_STORAGE_BACKEND == "firebase":
            if not settings.FIREBASE_STORAGE_BUCKET:
                print("[Startup ERROR] FIREBASE_STORAGE_ENABLED=true but FIREBASE_STORAGE_BUCKET is not set.")
            if not getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None):
                print(
                    "[Startup INFO] GOOGLE_APPLICATION_CREDENTIALS not set; "
                    "using Application Default Credentials (ADC)."
                )
    except Exception as exc:
        print(f"[Startup Warning] Storage backend initialisation issue: {exc}")

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
# Allow requests from localhost and all Vercel deployment domains (*.vercel.app|.*.onrender.com)
cors_regex = r"^https?:\/\/(.*\.vercel\.app|localhost|127\.0\.0\.1)(:[0-9]+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=cors_regex,
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
