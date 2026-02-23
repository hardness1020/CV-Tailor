"""
Unified exception handling for LLM services.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Import API exceptions - handle missing imports gracefully
try:
    from openai import (
        APIConnectionError,
        APIStatusError,
        RateLimitError,
        AuthenticationError,
        PermissionDeniedError,
        BadRequestError,
        InternalServerError
    )
except ImportError:
    # Create dummy exception classes if OpenAI is not installed
    class APIConnectionError(Exception): pass
    class APIStatusError(Exception): pass
    class RateLimitError(Exception): pass
    class AuthenticationError(Exception): pass
    class PermissionDeniedError(Exception): pass
    class BadRequestError(Exception): pass
    class InternalServerError(Exception): pass

try:
    import anthropic
    AnthropicError = anthropic.APIError
except ImportError:
    class AnthropicError(Exception): pass


class ErrorType(Enum):
    """Classification of error types for fallback logic"""
    RATE_LIMIT = "rate_limit"
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    BAD_REQUEST = "bad_request"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Recoverable, no fallback needed
    MEDIUM = "medium"     # May need fallback
    HIGH = "high"         # Definitely needs fallback
    CRITICAL = "critical" # Circuit breaker should open


class ExceptionHandler:
    """Unified exception handling with classification and fallback logic"""

    ERROR_MAPPING = {
        RateLimitError: (ErrorType.RATE_LIMIT, ErrorSeverity.HIGH),
        APIConnectionError: (ErrorType.CONNECTION, ErrorSeverity.HIGH),
        AuthenticationError: (ErrorType.AUTHENTICATION, ErrorSeverity.CRITICAL),
        PermissionDeniedError: (ErrorType.PERMISSION, ErrorSeverity.CRITICAL),
        BadRequestError: (ErrorType.BAD_REQUEST, ErrorSeverity.LOW),
        InternalServerError: (ErrorType.SERVER_ERROR, ErrorSeverity.HIGH),
        AnthropicError: (ErrorType.UNKNOWN, ErrorSeverity.MEDIUM),
    }

    @classmethod
    def classify_error(cls, error: Exception) -> Tuple[ErrorType, ErrorSeverity]:
        """Classify error type and severity"""
        error_class = type(error)

        # Check for exact matches
        if error_class in cls.ERROR_MAPPING:
            return cls.ERROR_MAPPING[error_class]

        # Check for inheritance
        for exception_type, (error_type, severity) in cls.ERROR_MAPPING.items():
            if isinstance(error, exception_type):
                return error_type, severity

        # Default classification
        return ErrorType.UNKNOWN, ErrorSeverity.MEDIUM

    @classmethod
    def should_trigger_circuit_breaker(cls, error: Exception) -> bool:
        """Determine if error should trigger circuit breaker"""
        error_type, severity = cls.classify_error(error)

        # Don't trigger circuit breaker for client errors (our fault)
        if error_type in [ErrorType.BAD_REQUEST, ErrorType.AUTHENTICATION, ErrorType.PERMISSION]:
            return False

        # Trigger for server errors and connection issues
        return severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]

    @classmethod
    def should_use_fallback(cls, error: Exception) -> bool:
        """Determine if error should trigger fallback model"""
        error_type, severity = cls.classify_error(error)

        # Use fallback for recoverable errors
        return severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]

    @classmethod
    def get_user_friendly_message(cls, error: Exception) -> str:
        """Get user-friendly error message"""
        error_type, severity = cls.classify_error(error)

        error_messages = {
            ErrorType.RATE_LIMIT: "Rate limit exceeded. Please try again in a moment.",
            ErrorType.CONNECTION: "Connection error. Please check your internet connection.",
            ErrorType.AUTHENTICATION: "Authentication failed. Please check API credentials.",
            ErrorType.PERMISSION: "Access denied to the requested model.",
            ErrorType.BAD_REQUEST: "Invalid request parameters.",
            ErrorType.SERVER_ERROR: "Service temporarily unavailable. Please try again.",
            ErrorType.UNKNOWN: "An unexpected error occurred. Please try again."
        }

        return error_messages.get(error_type, "An error occurred while processing your request.")

    @classmethod
    def log_error(cls, error: Exception, model_name: str, task_type: str, context: Dict[str, Any] = None):
        """Log error with appropriate level and context"""
        error_type, severity = cls.classify_error(error)
        context = context or {}

        log_context = {
            'model': model_name,
            'task_type': task_type,
            'error_type': error_type.value,
            'severity': severity.value,
            **context
        }

        if severity == ErrorSeverity.CRITICAL:
            logger.error(f"Critical error in {task_type} with {model_name}: {error}", extra=log_context)
        elif severity == ErrorSeverity.HIGH:
            logger.warning(f"High severity error in {task_type} with {model_name}: {error}", extra=log_context)
        elif severity == ErrorSeverity.MEDIUM:
            logger.info(f"Medium severity error in {task_type} with {model_name}: {error}", extra=log_context)
        else:
            logger.debug(f"Low severity error in {task_type} with {model_name}: {error}", extra=log_context)

    @classmethod
    def create_error_response(cls, error: Exception, model_name: str, processing_time_ms: int = 0) -> Dict[str, Any]:
        """Create standardized error response"""
        error_type, severity = cls.classify_error(error)

        return {
            'error': cls.get_user_friendly_message(error),
            'error_details': {
                'type': error_type.value,
                'severity': severity.value,
                'model': model_name,
                'processing_time_ms': processing_time_ms,
                'original_error': str(error)
            }
        }