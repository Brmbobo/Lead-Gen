"""
Retry logic with exponential backoff and circuit breaker pattern.

Provides resilient API calls with:
- Exponential backoff with jitter
- Circuit breaker to prevent cascade failures
- Configurable retry conditions
- Comprehensive logging
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

import structlog

from lead_gen.core.exceptions import (
    APIError,
    CircuitBreakerOpenError,
    LeadGenError,
    RateLimitError,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")
AsyncFunc = Callable[..., Awaitable[T]]


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.5  # 0-1, percentage of delay to randomize

    # Retry conditions
    retry_on_exceptions: tuple[type[Exception], ...] = (
        APIError,
        RateLimitError,
        asyncio.TimeoutError,
        ConnectionError,
    )
    retry_on_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay,
        )

        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    reset_timeout: float = 30.0  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max concurrent calls in half-open


@dataclass
class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascade failures by temporarily blocking requests
    to a failing service.

    States:
    - CLOSED: Normal operation
    - OPEN: Service failing, requests blocked
    - HALF_OPEN: Testing recovery with limited requests

    Example:
        >>> breaker = CircuitBreaker("openai")
        >>> async with breaker:
        ...     await call_openai()
    """

    service: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: datetime | None = field(default=None, init=False)
    half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def __aenter__(self) -> "CircuitBreaker":
        await self._before_call()
        return self

    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_val: Exception | None,
        exc_tb: object,
    ) -> None:
        if exc_val is None:
            await self._on_success()
        else:
            await self._on_failure(exc_val)

    async def _before_call(self) -> None:
        """Check circuit state before allowing a call."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_try_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is open for service '{self.service}'",
                        service=self.service,
                        failure_count=self.failure_count,
                        last_failure_time=self.last_failure_time,
                        reset_timeout=self.config.reset_timeout,
                    )

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker half-open limit reached for '{self.service}'",
                        service=self.service,
                        failure_count=self.failure_count,
                        last_failure_time=self.last_failure_time,
                        reset_timeout=self.config.reset_timeout,
                    )
                self.half_open_calls += 1

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls -= 1

                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            logger.warning(
                "circuit_breaker_failure",
                service=self.service,
                state=self.state.value,
                failure_count=self.failure_count,
                error=str(error),
            )

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls -= 1
                self._transition_to_open()

            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()

    def _should_try_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self.last_failure_time is None:
            return True

        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.config.reset_timeout

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.warning(
            "circuit_breaker_opened",
            service=self.service,
            failure_count=self.failure_count,
            reset_timeout=self.config.reset_timeout,
        )

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        logger.info(
            "circuit_breaker_half_open",
            service=self.service,
        )

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info(
            "circuit_breaker_closed",
            service=self.service,
        )

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "service": self.service,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


def retry_with_backoff(
    config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> Callable[[AsyncFunc[T]], AsyncFunc[T]]:
    """
    Decorator for retrying async functions with exponential backoff.

    Example:
        >>> @retry_with_backoff()
        ... async def call_api():
        ...     return await httpx.get("https://api.example.com")

        >>> @retry_with_backoff(
        ...     config=RetryConfig(max_retries=5),
        ...     circuit_breaker=CircuitBreaker("myservice"),
        ... )
        ... async def call_with_circuit_breaker():
        ...     return await httpx.get("https://api.example.com")
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: AsyncFunc[T]) -> AsyncFunc[T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    if circuit_breaker:
                        async with circuit_breaker:
                            return await func(*args, **kwargs)
                    else:
                        return await func(*args, **kwargs)

                except CircuitBreakerOpenError:
                    # Don't retry if circuit is open
                    raise

                except config.retry_on_exceptions as e:
                    last_exception = e

                    # Check if we should retry
                    should_retry = True
                    if isinstance(e, APIError):
                        should_retry = e.is_retryable
                        if e.status_code and e.status_code not in config.retry_on_status_codes:
                            should_retry = False

                    if not should_retry or attempt >= config.max_retries:
                        raise

                    # Calculate delay
                    if isinstance(e, RateLimitError) and e.retry_after_seconds:
                        delay = e.retry_after_seconds
                    else:
                        delay = config.calculate_delay(attempt)

                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=config.max_retries,
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper

    return decorator


# Registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if service not in _circuit_breakers:
        _circuit_breakers[service] = CircuitBreaker(
            service=service,
            config=config or CircuitBreakerConfig(),
        )
    return _circuit_breakers[service]


def reset_circuit_breakers() -> None:
    """Reset all circuit breakers (for testing)."""
    _circuit_breakers.clear()
