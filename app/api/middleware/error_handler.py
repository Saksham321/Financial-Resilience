"""
Global Exception Handler Middleware & Registrars
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from app.core.exceptions import AppException
from app.core.logging import logger
from datetime import datetime, timezone

def register_exception_handlers(app: FastAPI):
    """Registers standard exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.warning(
            "Application exception intercepted",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            path=request.url.path
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": correlation_id
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = getattr(request.state, "correlation_id", None)
        errors = [{"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in exc.errors()]
        logger.warning(
            "Validation exception intercepted",
            errors=errors,
            path=request.url.path
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": {"validation_errors": jsonable_encoder(errors)},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": correlation_id
                }
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(
            "Unhandled server exception",
            exc_info=exc,
            path=request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact support with correlation ID.",
                    "details": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": correlation_id
                }
            }
        )
