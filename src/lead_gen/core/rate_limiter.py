"""
Rate limiting implementation using token bucket algorithm.

Provides per-service rate limiting with:
- Configurable limits per minute
- Async-safe implementation
- Automatic token replenishment
- Wait-for-token support
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

import structlog

from lead_gen.core.exceptions import RateLimitError

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limiter."""

    requests_per_minute: int = 60
    burst_size: int | None = None  # Defaults to requests_per_minute

    def __post_init__(self) -> None:
        if self.burst_size is None:
            self.burst_size = self.requests_per_minute


@dataclass
class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Tokens are added at a constant rate up to the bucket capacity.
    Each request consumes one token.
    """

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    async def acquire(self, tokens: int = 1, wait: bool = True) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire
            wait: If True, wait for tokens to become available

        Returns:
            True if tokens were acquired, False if not available and wait=False

        Raises:
            RateLimitError: If wait=False and tokens not available
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not wait:
                wait_time = (tokens - self.tokens) / self.refill_rate
                raise RateLimitError(
                    f"Rate limit exceeded, retry after {wait_time:.2f}s",
                    retry_after_seconds=wait_time,
                    limit=self.capacity,
                    remaining=int(self.tokens),
                )

        # Wait for tokens (outside lock to allow other operations)
        wait_time = (tokens - self.tokens) / self.refill_rate
        logger.debug(
            "rate_limit_waiting",
            wait_time=wait_time,
            tokens_needed=tokens,
            tokens_available=self.tokens,
        )
        await asyncio.sleep(wait_time)

        # Try again after waiting
        return await self.acquire(tokens, wait=False)

    @property
    def available_tokens(self) -> int:
        """Get current available tokens (without acquiring lock)."""
        return int(self.tokens)


class RateLimiter:
    """
    Multi-service rate limiter.

    Manages separate rate limits for different services.
    Thread-safe and async-safe.

    Example:
        >>> limiter = RateLimiter()
        >>> limiter.add_service("openai", RateLimitConfig(requests_per_minute=60))
        >>> async with limiter.acquire("openai"):
        ...     await call_openai_api()
    """

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._configs: dict[str, RateLimitConfig] = {}

    def add_service(self, name: str, config: RateLimitConfig) -> None:
        """
        Add a rate-limited service.

        Args:
            name: Service identifier
            config: Rate limit configuration
        """
        self._configs[name] = config
        self._buckets[name] = TokenBucket(
            capacity=config.burst_size or config.requests_per_minute,
            refill_rate=config.requests_per_minute / 60.0,
        )
        logger.info(
            "rate_limiter_configured",
            service=name,
            requests_per_minute=config.requests_per_minute,
            burst_size=config.burst_size,
        )

    def remove_service(self, name: str) -> None:
        """Remove a rate-limited service."""
        self._buckets.pop(name, None)
        self._configs.pop(name, None)

    async def acquire(
        self,
        service: str,
        tokens: int = 1,
        wait: bool = True,
    ) -> "RateLimitContext":
        """
        Acquire rate limit tokens for a service.

        Args:
            service: Service name
            tokens: Number of tokens to acquire
            wait: Wait for tokens if not available

        Returns:
            Context manager that can be used with async with
        """
        if service not in self._buckets:
            # Service not configured, allow unlimited
            logger.warning("rate_limiter_service_not_configured", service=service)
            return RateLimitContext(None, service, tokens)

        bucket = self._buckets[service]
        await bucket.acquire(tokens, wait=wait)
        return RateLimitContext(bucket, service, tokens)

    def get_status(self, service: str) -> dict[str, int | float]:
        """Get current rate limit status for a service."""
        if service not in self._buckets:
            return {"available": -1, "capacity": -1, "refill_rate": -1}

        bucket = self._buckets[service]
        return {
            "available": bucket.available_tokens,
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate,
        }

    def get_all_status(self) -> dict[str, dict[str, int | float]]:
        """Get rate limit status for all services."""
        return {name: self.get_status(name) for name in self._buckets}


@dataclass
class RateLimitContext:
    """Context manager for rate limit acquisition."""

    bucket: TokenBucket | None
    service: str
    tokens: int

    async def __aenter__(self) -> "RateLimitContext":
        return self

    async def __aexit__(self, *args: object) -> None:
        # Tokens are consumed on acquire, nothing to release
        pass


# Global rate limiter instance
_global_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def configure_rate_limits(
    google_places: int = 60,
    openai: int = 60,
    hunter: int = 30,
    sheets: int = 60,
) -> RateLimiter:
    """
    Configure rate limits for all services.

    Args:
        google_places: Requests per minute for Google Places API
        openai: Requests per minute for OpenAI API
        hunter: Requests per minute for Hunter.io API
        sheets: Requests per minute for Google Sheets API

    Returns:
        Configured RateLimiter instance
    """
    limiter = get_rate_limiter()

    limiter.add_service("google_places", RateLimitConfig(requests_per_minute=google_places))
    limiter.add_service("openai", RateLimitConfig(requests_per_minute=openai))
    limiter.add_service("hunter", RateLimitConfig(requests_per_minute=hunter))
    limiter.add_service("sheets", RateLimitConfig(requests_per_minute=sheets))

    return limiter


def rate_limited(service: str, tokens: int = 1, wait: bool = True) -> Callable:
    """
    Decorator to rate limit a function.

    Example:
        >>> @rate_limited("openai")
        ... async def generate_message(prompt: str) -> str:
        ...     return await openai.complete(prompt)
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: object, **kwargs: object) -> object:
            limiter = get_rate_limiter()
            async with await limiter.acquire(service, tokens, wait):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
