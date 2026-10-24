"""
Application Domain Exceptions and FastAPI Error Handlers
"""
from typing import Optional, List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.common.schemas import ErrorResponse, ErrorDetail


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST", details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, code="NOT_FOUND")


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict occurred"):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, code="CONFLICT")


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED")


class ForbiddenException(AppException):
    def __init__(self, message: str = "Action forbidden for current role"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=exc.message,
            code=exc.code,
            details=exc.details,
        ).model_dump(mode="json"),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            code="VALIDATION_ERROR",
            message=err.get("msg", "Invalid value"),
            field=".".join(str(loc) for loc in err.get("loc", [])),
        )
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error="Validation failed for request parameters",
            code="UNPROCESSABLE_ENTITY",
            details=details,
        ).model_dump(mode="json"),
    )
