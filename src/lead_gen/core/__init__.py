"""
Core infrastructure module for Lead-Gen.

This module provides foundational components:
- Configuration management with Pydantic Settings
- Custom exception hierarchy
- Rate limiting with token bucket algorithm
- Retry logic with circuit breaker pattern
- Enterprise secret management
- GDPR compliance utilities
- Input sanitization for security
"""

from lead_gen.core.config import Settings, get_settings
from lead_gen.core.exceptions import (
    LeadGenError,
    ConfigurationError,
    APIError,
    RateLimitError,
    ValidationError,
    GDPRError,
    SecurityError,
)
from lead_gen.core.rate_limiter import RateLimiter, RateLimitConfig
from lead_gen.core.retry import retry_with_backoff, CircuitBreaker, CircuitState

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Exceptions
    "LeadGenError",
    "ConfigurationError",
    "APIError",
    "RateLimitError",
    "ValidationError",
    "GDPRError",
    "SecurityError",
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    # Retry
    "retry_with_backoff",
    "CircuitBreaker",
    "CircuitState",
]
