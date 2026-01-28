"""
Custom exception hierarchy for Lead-Gen.

All exceptions inherit from LeadGenError for easy catching.
Each exception type includes structured context for logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(kw_only=True)
class ErrorContext:
    """Structured context for error tracking."""

    error_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    service: str | None = None
    operation: str | None = None
    correlation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            **self.extra,
        }


class LeadGenError(Exception):
    """
    Base exception for all Lead-Gen errors.

    All custom exceptions should inherit from this class.
    Includes structured context for observability.

    Example:
        >>> try:
        ...     raise LeadGenError("Something went wrong", service="places")
        ... except LeadGenError as e:
        ...     print(e.context.error_id)
    """

    def __init__(
        self,
        message: str,
        *,
        service: str | None = None,
        operation: str | None = None,
        correlation_id: str | None = None,
        cause: Exception | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = ErrorContext(
            service=service,
            operation=operation,
            correlation_id=correlation_id,
            extra=extra,
        )

    def __str__(self) -> str:
        parts = [self.message]
        if self.context.service:
            parts.append(f"[service={self.context.service}]")
        if self.context.operation:
            parts.append(f"[operation={self.context.operation}]")
        if self.cause:
            parts.append(f"[caused_by={type(self.cause).__name__}: {self.cause}]")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_id={self.context.error_id!r})"
        )


class ConfigurationError(LeadGenError):
    """
    Raised when configuration is invalid or missing.

    Examples:
        - Missing required API key
        - Invalid environment variable value
        - Malformed configuration file
    """

    def __init__(
        self,
        message: str,
        *,
        config_key: str | None = None,
        expected_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            service="config",
            config_key=config_key,
            expected_type=expected_type,
            **kwargs,
        )
        self.config_key = config_key
        self.expected_type = expected_type


class APIError(LeadGenError):
    """
    Raised when an external API call fails.

    Includes HTTP status code and response body for debugging.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        url: str | None = None,
        method: str = "GET",
        **kwargs: Any,
    ) -> None:
        # Mask sensitive data in URL
        safe_url = self._mask_url(url) if url else None

        super().__init__(
            message,
            status_code=status_code,
            response_body=response_body[:500] if response_body else None,  # Truncate
            url=safe_url,
            method=method,
            **kwargs,
        )
        self.status_code = status_code
        self.response_body = response_body
        self.url = url
        self.method = method

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask API keys in URLs."""
        import re
        # Mask common API key patterns
        patterns = [
            (r"(key=)[^&]+", r"\1***"),
            (r"(api_key=)[^&]+", r"\1***"),
            (r"(apikey=)[^&]+", r"\1***"),
            (r"(token=)[^&]+", r"\1***"),
        ]
        for pattern, replacement in patterns:
            url = re.sub(pattern, replacement, url, flags=re.IGNORECASE)
        return url

    @property
    def is_retryable(self) -> bool:
        """Check if this error should be retried."""
        if self.status_code is None:
            return True  # Network errors are retryable
        # Retry server errors and rate limits
        return self.status_code >= 500 or self.status_code == 429

    @property
    def is_rate_limit(self) -> bool:
        """Check if this is a rate limit error."""
        return self.status_code == 429


class RateLimitError(LeadGenError):
    """
    Raised when rate limit is exceeded.

    Includes retry-after information when available.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
        limit: int | None = None,
        remaining: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            retry_after_seconds=retry_after_seconds,
            limit=limit,
            remaining=remaining,
            **kwargs,
        )
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit
        self.remaining = remaining


class ValidationError(LeadGenError):
    """
    Raised when input validation fails.

    Used for both Pydantic validation errors and custom validation.
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        field_value: Any = None,
        constraint: str | None = None,
        **kwargs: Any,
    ) -> None:
        # Don't log potentially sensitive field values
        safe_value = "***" if field_value is not None else None

        super().__init__(
            message,
            operation="validation",
            field_name=field_name,
            field_value=safe_value,
            constraint=constraint,
            **kwargs,
        )
        self.field_name = field_name
        self.field_value = field_value
        self.constraint = constraint


class GDPRError(LeadGenError):
    """
    Raised for GDPR compliance violations.

    Used when data processing would violate GDPR requirements.
    """

    def __init__(
        self,
        message: str,
        *,
        article: str | None = None,
        data_subject_id: str | None = None,
        required_action: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            service="gdpr",
            article=article,
            data_subject_id=data_subject_id,
            required_action=required_action,
            **kwargs,
        )
        self.article = article
        self.data_subject_id = data_subject_id
        self.required_action = required_action


class SecurityError(LeadGenError):
    """
    Raised for security-related issues.

    Examples:
        - Potential injection attack detected
        - Invalid authentication
        - Unauthorized access attempt
    """

    def __init__(
        self,
        message: str,
        *,
        threat_type: str | None = None,
        blocked: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            service="security",
            threat_type=threat_type,
            blocked=blocked,
            **kwargs,
        )
        self.threat_type = threat_type
        self.blocked = blocked


class CircuitBreakerOpenError(LeadGenError):
    """
    Raised when circuit breaker is open.

    Indicates that the service is currently unavailable
    and calls are being rejected to prevent cascade failures.
    """

    def __init__(
        self,
        message: str,
        *,
        service: str,
        failure_count: int,
        last_failure_time: datetime | None = None,
        reset_timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            service=service,
            operation="circuit_breaker",
            failure_count=failure_count,
            reset_timeout=reset_timeout,
            **kwargs,
        )
        self.failure_count = failure_count
        self.last_failure_time = last_failure_time
        self.reset_timeout = reset_timeout


class WorkflowError(LeadGenError):
    """
    Raised when workflow execution fails.

    Includes information about which step failed.
    """

    def __init__(
        self,
        message: str,
        *,
        workflow_name: str,
        step_name: str | None = None,
        step_index: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            service="workflow",
            operation=workflow_name,
            step_name=step_name,
            step_index=step_index,
            **kwargs,
        )
        self.workflow_name = workflow_name
        self.step_name = step_name
        self.step_index = step_index
