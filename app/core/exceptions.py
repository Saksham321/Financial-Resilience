"""
Standardized Application Exceptions & Error Models
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Contextual error metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None

class AppException(Exception):
    """Base application exception."""
    status_code: int = 500
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class EntityNotFoundError(AppException):
    status_code = 404
    error_code = "ENTITY_NOT_FOUND"

class AuthenticationError(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"

class AuthorizationError(AppException):
    status_code = 403
    error_code = "INSUFFICIENT_PERMISSIONS"

class DuplicateResourceError(AppException):
    status_code = 409
    error_code = "RESOURCE_CONFLICT"

class ValidationException(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

class ExternalServiceError(AppException):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_UNAVAILABLE"

class FinancialCalculationError(AppException):
    status_code = 400
    error_code = "FINANCIAL_CALCULATION_ERROR"

class AffordabilityExceededError(AppException):
    status_code = 422
    error_code = "AFFORDABILITY_CRITERIA_UNMET"
