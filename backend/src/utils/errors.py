"""
SmartAP Custom Error Classes and Error Response Models

Provides standardized error handling across the application.
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException, status


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error_code: str
    message: str
    detail: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None
    path: Optional[str] = None
    suggestions: Optional[List[str]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SmartAPError(Exception):
    """Base exception for all SmartAP errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SMARTAP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        self.suggestions = suggestions or []
        super().__init__(message)
    
    def to_response(self, request_id: Optional[str] = None, path: Optional[str] = None) -> ErrorResponse:
        """Convert to ErrorResponse model."""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            detail=self.detail,
            request_id=request_id,
            path=path,
            suggestions=self.suggestions,
        )
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error_code": self.error_code,
                "message": self.message,
                "detail": self.detail,
                "suggestions": self.suggestions,
            }
        )


class ValidationError(SmartAPError):
    """Validation errors for input data."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            suggestions=["Check the input data format", "Refer to API documentation"],
        )
        self.field = field


class NotFoundError(SmartAPError):
    """Resource not found errors."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        detail: Optional[str] = None,
    ):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            suggestions=[
                f"Verify the {resource_type.lower()} ID is correct",
                f"Check if the {resource_type.lower()} has been deleted",
            ],
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthenticationError(SmartAPError):
    """Authentication failures."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        detail: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            suggestions=[
                "Check your credentials",
                "Ensure your token has not expired",
                "Try logging in again",
            ],
        )


class AuthorizationError(SmartAPError):
    """Authorization/permission errors."""
    
    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        required_role: Optional[str] = None,
        detail: Optional[str] = None,
    ):
        suggestions = ["Contact your administrator for access"]
        if required_role:
            suggestions.insert(0, f"Required role: {required_role}")
        
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            suggestions=suggestions,
        )
        self.required_role = required_role


class ExternalServiceError(SmartAPError):
    """Errors from external services (ERP, OCR, AI, etc.)."""
    
    def __init__(
        self,
        service_name: str,
        message: str,
        original_error: Optional[str] = None,
        retryable: bool = True,
    ):
        super().__init__(
            message=f"{service_name} error: {message}",
            error_code=f"EXTERNAL_SERVICE_ERROR_{service_name.upper().replace(' ', '_')}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=original_error,
            suggestions=[
                f"The {service_name} service may be temporarily unavailable",
                "Try again in a few moments" if retryable else "Contact support if the issue persists",
            ],
        )
        self.service_name = service_name
        self.retryable = retryable


class RateLimitError(SmartAPError):
    """Rate limit exceeded errors."""
    
    def __init__(
        self,
        retry_after: int = 60,
        detail: Optional[str] = None,
    ):
        super().__init__(
            message="Rate limit exceeded. Please slow down.",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            suggestions=[
                f"Wait {retry_after} seconds before retrying",
                "Reduce the frequency of your requests",
            ],
        )
        self.retry_after = retry_after


class CircuitBreakerOpenError(SmartAPError):
    """Circuit breaker is open - service unavailable."""
    
    def __init__(
        self,
        service_name: str,
        retry_after: int = 30,
    ):
        super().__init__(
            message=f"Service '{service_name}' is temporarily unavailable due to recent failures",
            error_code=f"CIRCUIT_BREAKER_OPEN_{service_name.upper().replace(' ', '_')}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Circuit breaker tripped after multiple failures",
            suggestions=[
                f"Wait {retry_after} seconds before retrying",
                "The service will automatically recover when the underlying issue is resolved",
            ],
        )
        self.service_name = service_name
        self.retry_after = retry_after


# Exception-to-response mapping for FastAPI exception handlers
ERROR_MAPPINGS = {
    SmartAPError: lambda e: (e.status_code, e.to_response()),
    ValidationError: lambda e: (e.status_code, e.to_response()),
    NotFoundError: lambda e: (e.status_code, e.to_response()),
    AuthenticationError: lambda e: (e.status_code, e.to_response()),
    AuthorizationError: lambda e: (e.status_code, e.to_response()),
    ExternalServiceError: lambda e: (e.status_code, e.to_response()),
    RateLimitError: lambda e: (e.status_code, e.to_response()),
    CircuitBreakerOpenError: lambda e: (e.status_code, e.to_response()),
}
