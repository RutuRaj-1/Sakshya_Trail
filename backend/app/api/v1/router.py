"""
API v1 Main Router
Aggregates endpoints and modular sub-routers.
"""
from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.institutions.router import router as institutions_router
from app.modules.instruments.router import router as instruments_router
from app.modules.documents.router import router as documents_router
from app.modules.audit.router import router as audit_router
from app.modules.dashboard.router import router as dashboard_router

api_v1_router = APIRouter()

# Core system routes
api_v1_router.include_router(health_router)

# Domain module routes
api_v1_router.include_router(auth_router)
api_v1_router.include_router(institutions_router)
api_v1_router.include_router(instruments_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(dashboard_router)
