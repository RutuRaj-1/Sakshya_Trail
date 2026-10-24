"""
Common Pydantic Schemas for Standardized Responses
"""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status (e.g. alive, healthy)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str = "FDR Sentinel API"
    version: str = "0.1.0"
    environment: str = "development"


class DatabaseHealth(BaseModel):
    status: str
    is_ready: bool
    dialect: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class ReadinessResponse(BaseModel):
    status: str = Field(..., description="System overall readiness (ready, degraded, not_ready)")
    is_ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, Any]


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: str = "INTERNAL_ERROR"
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    meta: PaginationMeta
