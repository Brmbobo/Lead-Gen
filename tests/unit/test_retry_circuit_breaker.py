"""
Comprehensive unit tests for retry logic and circuit breaker implementation.

Tests cover:
1. RetryConfig - delay calculation, jitter
2. CircuitBreaker states (CLOSED → OPEN → HALF_OPEN → CLOSED)
3. CircuitBreaker failure threshold triggers OPEN
4. CircuitBreaker success threshold triggers CLOSED
5. CircuitBreaker timeout for reset
6. retry_with_backoff decorator - successful retry
7. retry_with_backoff decorator - max retries exceeded
8. retry_with_backoff with circuit breaker integration
9. get_circuit_breaker registry
10. reset_circuit_breakers
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lead_gen.core.exceptions import (
    APIError,
    CircuitBreakerOpenError,
    LeadGenError,
    RateLimitError,
)
from lead_gen.core.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryConfig,
    get_circuit_breaker,
    reset_circuit_breakers,
    retry_with_backoff,
)


# ============================================================================
# RetryConfig Tests
# ============================================================================


class TestRetryConfig:
    """Test RetryConfig delay calculation and jitter."""

    def test_retry_config_default_values(self):
        """Test RetryConfig has correct default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_factor == 0.5

    def test_calculate_delay_without_jitter_attempt_0(self):
        """Test delay calculation for attempt 0 without jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = config.calculate_delay(0)
        # 1.0 * (2.0 ** 0) = 1.0
        assert delay == 1.0

    def test_calculate_delay_without_jitter_attempt_1(self):
        """Test delay calculation for attempt 1 without jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = config.calculate_delay(1)
        # 1.0 * (2.0 ** 1) = 2.0
        assert delay == 2.0

    def test_calculate_delay_without_jitter_attempt_2(self):
        """Test delay calculation for attempt 2 without jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = config.calculate_delay(2)
        # 1.0 * (2.0 ** 2) = 4.0
        assert delay == 4.0

    def test_calculate_delay_without_jitter_attempt_3(self):
        """Test delay calculation for attempt 3 without jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = config.calculate_delay(3)
        # 1.0 * (2.0 ** 3) = 8.0
        assert delay == 8.0

    def test_calculate_delay_respects_max_delay(self):
        """Test that delay calculation respects max_delay cap."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )
        delay = config.calculate_delay(10)  # Would be 1024 without cap
        assert delay == 5.0

    def test_calculate_delay_with_jitter_varies(self):
        """Test that jitter produces varying delays."""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, jitter=True, jitter_factor=0.5)
        delays = [config.calculate_delay(2) for _ in range(20)]

        # With jitter, delays should vary
        assert len(set(delays)) > 1

        # All delays should be within expected range
        # base_delay * (exponential_base ** 2) = 10.0 * 4 = 40.0
        # jitter_range = 40.0 * 0.5 = 20.0
        # range: 40.0 - 20.0 to 40.0 + 20.0 = 20.0 to 60.0
        for delay in delays:
            assert 20.0 <= delay <= 60.0

    def test_calculate_delay_with_jitter_never_negative(self):
        """Test that jitter never produces negative delays."""
        config = RetryConfig(base_delay=0.1, exponential_base=2.0, jitter=True, jitter_factor=0.9)

        for attempt in range(10):
            delay = config.calculate_delay(attempt)
            assert delay >= 0

    def test_calculate_delay_custom_exponential_base(self):
        """Test delay calculation with custom exponential base."""
        config = RetryConfig(base_delay=1.0, exponential_base=3.0, jitter=False)

        assert config.calculate_delay(0) == 1.0   # 1.0 * (3.0 ** 0) = 1.0
        assert config.calculate_delay(1) == 3.0   # 1.0 * (3.0 ** 1) = 3.0
        assert config.calculate_delay(2) == 9.0   # 1.0 * (3.0 ** 2) = 9.0
        assert config.calculate_delay(3) == 27.0  # 1.0 * (3.0 ** 3) = 27.0

    def test_calculate_delay_custom_base_delay(self):
        """Test delay calculation with custom base delay."""
        config = RetryConfig(base_delay=5.0, exponential_base=2.0, jitter=False)

        assert config.calculate_delay(0) == 5.0   # 5.0 * (2.0 ** 0) = 5.0
        assert config.calculate_delay(1) == 10.0  # 5.0 * (2.0 ** 1) = 10.0
        assert config.calculate_delay(2) == 20.0  # 5.0 * (2.0 ** 2) = 20.0


# ============================================================================
# CircuitBreaker Tests
# ============================================================================


class TestCircuitBreakerStates:
    """Test CircuitBreaker state transitions."""

    @pytest.fixture(autouse=True)
    def reset_breakers(self):
        """Reset circuit breakers before each test."""
        reset_circuit_breakers()

    def test_circuit_breaker_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test-service")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_allows_requests(self):
        """Test that CLOSED state allows requests through."""
        breaker = CircuitBreaker("test-service")

        async with breaker:
            # Request should be allowed
            pass

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_resets_failure_count(self):
        """Test that success in CLOSED state resets failure count."""
        breaker = CircuitBreaker("test-service")
        breaker.failure_count = 2

        async with breaker:
            pass  # Success

        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_increments_count(self):
        """Test that failures increment failure count."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker("test-service", config=config)

        try:
            async with breaker:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_open_on_threshold(self):
        """Test CLOSED → OPEN transition when failure threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test-service", config=config)

        # Fail 3 times to reach threshold
        for i in range(3):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_requests(self):
        """Test that OPEN state blocks requests."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test-service", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Next request should be blocked
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async with breaker:
                pass

        assert "circuit breaker is open" in str(exc_info.value).lower()
        assert exc_info.value.failure_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_half_open_after_timeout(self):
        """Test OPEN → HALF_OPEN transition after reset timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, reset_timeout=0.1)
        breaker = CircuitBreaker("test-service", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.15)

        # Next request should transition to HALF_OPEN
        async with breaker:
            pass  # Success

        # After success in HALF_OPEN, we need more successes to close
        # So state might be HALF_OPEN or CLOSED depending on success_threshold
        assert breaker.state in (CircuitState.HALF_OPEN, CircuitState.CLOSED)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_closed_on_success_threshold(self):
        """Test HALF_OPEN → CLOSED transition after success threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            reset_timeout=0.1,
        )
        breaker = CircuitBreaker("test-service", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.15)

        # Make successful requests to reach success threshold
        for i in range(2):
            async with breaker:
                pass  # Success

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_open_on_failure(self):
        """Test HALF_OPEN → OPEN transition on failure."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            reset_timeout=0.1,
        )
        breaker = CircuitBreaker("test-service", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.15)

        # Fail in HALF_OPEN state
        try:
            async with breaker:
                raise ValueError("Test error in half-open")
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_max_calls_limit(self):
        """Test HALF_OPEN state enforces max concurrent calls limit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.1,
            half_open_max_calls=2,
        )
        breaker = CircuitBreaker("test-service", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Test error {i}")
            except ValueError:
                pass

        # Wait for reset timeout
        await asyncio.sleep(0.15)

        # Start 2 concurrent calls (max allowed)
        async def slow_call():
            async with breaker:
                await asyncio.sleep(0.1)

        # Start tasks but don't await them yet
        task1 = asyncio.create_task(slow_call())
        task2 = asyncio.create_task(slow_call())

        # Give tasks time to enter the context
        await asyncio.sleep(0.01)

        # Third call should be rejected
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async with breaker:
                pass

        assert "half-open limit reached" in str(exc_info.value).lower()

        # Wait for tasks to complete
        await task1
        await task2

    @pytest.mark.asyncio
    async def test_circuit_breaker_get_status(self):
        """Test get_status returns correct circuit breaker status."""
        breaker = CircuitBreaker("test-service")

        status = breaker.get_status()

        assert status["service"] == "test-service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["last_failure_time"] is None

    @pytest.mark.asyncio
    async def test_circuit_breaker_get_status_after_failure(self):
        """Test get_status returns updated status after failure."""
        breaker = CircuitBreaker("test-service")

        try:
            async with breaker:
                raise ValueError("Test error")
        except ValueError:
            pass

        status = breaker.get_status()

        assert status["service"] == "test-service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 1
        assert status["last_failure_time"] is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_last_failure_time(self):
        """Test that last_failure_time is recorded on failure."""
        breaker = CircuitBreaker("test-service")

        before = datetime.now(timezone.utc)

        try:
            async with breaker:
                raise ValueError("Test error")
        except ValueError:
            pass

        after = datetime.now(timezone.utc)

        assert breaker.last_failure_time is not None
        assert before <= breaker.last_failure_time <= after


# ============================================================================
# retry_with_backoff Decorator Tests
# ============================================================================


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_retry_successful_execution_no_retry(self):
        """Test successful execution without any retries."""
        call_count = 0

        @retry_with_backoff()
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_successful_after_failures(self):
        """Test successful execution after some failures."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Temporary error", status_code=500)
            return "success"

        result = await flaky_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_max_retries_exceeded(self):
        """Test that max retries is respected and exception is raised."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise APIError("Permanent error", status_code=500)

        with pytest.raises(APIError):
            await always_fails()

        # Should be called 3 times: initial + 2 retries
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_non_retryable_exception_not_retried(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")

        with pytest.raises(ValueError):
            await raises_non_retryable()

        # Should only be called once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_timeout_error_is_retried(self):
        """Test that asyncio.TimeoutError is retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def times_out():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError()
            return "success"

        result = await times_out()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_connection_error_is_retried(self):
        """Test that ConnectionError is retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def connection_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"

        result = await connection_fails()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_rate_limit_error_is_retried(self):
        """Test that RateLimitError is retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Rate limited")
            return "success"

        result = await rate_limited()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_rate_limit_uses_retry_after(self):
        """Test that RateLimitError retry_after_seconds is used for delay."""
        call_count = 0
        delays = []

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)  # Use small delay for testing

        with patch("asyncio.sleep", side_effect=mock_sleep):
            @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=1.0))
            async def rate_limited():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise RateLimitError("Rate limited", retry_after_seconds=5.0)
                return "success"

            result = await rate_limited()

        assert result == "success"
        assert call_count == 2
        # Should use retry_after_seconds instead of calculated delay
        assert delays[0] == 5.0

    @pytest.mark.asyncio
    async def test_retry_api_error_non_retryable_status_code(self):
        """Test that APIError with non-retryable status code is not retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def bad_request():
            nonlocal call_count
            call_count += 1
            raise APIError("Bad request", status_code=400)

        with pytest.raises(APIError):
            await bad_request()

        # Should only be called once (400 is not retryable)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_api_error_retryable_status_code_500(self):
        """Test that APIError with 500 status code is retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def server_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("Server error", status_code=500)
            return "success"

        result = await server_error()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_api_error_retryable_status_code_429(self):
        """Test that APIError with 429 status code is retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.01))
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("Rate limited", status_code=429)
            return "success"

        result = await rate_limited()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_api_error_is_retryable_false(self):
        """Test that APIError with is_retryable=False is not retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def non_retryable_api_error():
            nonlocal call_count
            call_count += 1
            # APIError with 400 status has is_retryable=False
            raise APIError("Client error", status_code=400)

        with pytest.raises(APIError):
            await non_retryable_api_error()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_circuit_breaker_open_not_retried(self):
        """Test that CircuitBreakerOpenError is not retried."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def circuit_open():
            nonlocal call_count
            call_count += 1
            raise CircuitBreakerOpenError(
                "Circuit open",
                service="test",
                failure_count=5,
            )

        with pytest.raises(CircuitBreakerOpenError):
            await circuit_open()

        # Should not be retried
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_integration(self):
        """Test retry_with_backoff works with circuit breaker."""
        call_count = 0
        breaker = CircuitBreaker("test-service", config=CircuitBreakerConfig(failure_threshold=10))

        @retry_with_backoff(
            config=RetryConfig(max_retries=2, base_delay=0.01),
            circuit_breaker=breaker,
        )
        async def with_breaker():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("Temporary error", status_code=500)
            return "success"

        result = await with_breaker()

        assert result == "success"
        assert call_count == 2
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after failures."""
        call_count = 0
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test-service", config=config)

        @retry_with_backoff(
            config=RetryConfig(max_retries=1, base_delay=0.01),
            circuit_breaker=breaker,
        )
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise APIError("Error", status_code=500)

        # First call: fails twice (initial + 1 retry), circuit should open
        with pytest.raises(APIError):
            await always_fails()

        assert breaker.state == CircuitState.OPEN

        # Second call should be blocked by circuit breaker
        call_count = 0
        with pytest.raises(CircuitBreakerOpenError):
            await always_fails()

        # Function should not have been called (circuit blocked it)
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_retry_delay_is_calculated_correctly(self):
        """Test that retry delay is calculated correctly."""
        call_count = 0
        delays = []

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.01)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            config = RetryConfig(
                max_retries=3,
                base_delay=1.0,
                exponential_base=2.0,
                jitter=False,
            )

            @retry_with_backoff(config=config)
            async def fails_three_times():
                nonlocal call_count
                call_count += 1
                if call_count < 4:
                    raise APIError("Error", status_code=500)
                return "success"

            result = await fails_three_times()

        assert result == "success"
        assert call_count == 4
        # Delays should be: 1.0, 2.0, 4.0 (for attempts 0, 1, 2)
        assert len(delays) == 3
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

    @pytest.mark.asyncio
    async def test_retry_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        @retry_with_backoff()
        async def my_func():
            """This is my function."""
            return "result"

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "This is my function."


# ============================================================================
# Circuit Breaker Registry Tests
# ============================================================================


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functions."""

    @pytest.fixture(autouse=True)
    def reset_breakers(self):
        """Reset circuit breakers before each test."""
        reset_circuit_breakers()

    def test_get_circuit_breaker_creates_new_breaker(self):
        """Test that get_circuit_breaker creates a new breaker."""
        breaker = get_circuit_breaker("service1")

        assert breaker.service == "service1"
        assert breaker.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_existing_breaker(self):
        """Test that get_circuit_breaker returns existing breaker."""
        breaker1 = get_circuit_breaker("service1")
        breaker2 = get_circuit_breaker("service1")

        assert breaker1 is breaker2

    def test_get_circuit_breaker_different_services(self):
        """Test that different services get different breakers."""
        breaker1 = get_circuit_breaker("service1")
        breaker2 = get_circuit_breaker("service2")

        assert breaker1 is not breaker2
        assert breaker1.service == "service1"
        assert breaker2.service == "service2"

    def test_get_circuit_breaker_with_custom_config(self):
        """Test that get_circuit_breaker accepts custom config."""
        config = CircuitBreakerConfig(failure_threshold=10, reset_timeout=60.0)
        breaker = get_circuit_breaker("service1", config=config)

        assert breaker.config.failure_threshold == 10
        assert breaker.config.reset_timeout == 60.0

    def test_reset_circuit_breakers_clears_registry(self):
        """Test that reset_circuit_breakers clears all breakers."""
        breaker1 = get_circuit_breaker("service1")
        breaker2 = get_circuit_breaker("service2")

        reset_circuit_breakers()

        # Getting breakers again should create new instances
        new_breaker1 = get_circuit_breaker("service1")
        new_breaker2 = get_circuit_breaker("service2")

        assert new_breaker1 is not breaker1
        assert new_breaker2 is not breaker2

    @pytest.mark.asyncio
    async def test_reset_circuit_breakers_resets_state(self):
        """Test that reset_circuit_breakers clears breaker state."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = get_circuit_breaker("service1", config=config)

        # Trigger OPEN state
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError(f"Error {i}")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Reset and get new breaker
        reset_circuit_breakers()
        new_breaker = get_circuit_breaker("service1")

        assert new_breaker.state == CircuitState.CLOSED
        assert new_breaker.failure_count == 0


# ============================================================================
# Additional Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and complex scenarios."""

    @pytest.fixture(autouse=True)
    def reset_breakers(self):
        """Reset circuit breakers before each test."""
        reset_circuit_breakers()

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_success(self):
        """Test circuit breaker with concurrent successful requests."""
        breaker = CircuitBreaker("test-service")
        results = []

        async def make_request(request_id: int):
            async with breaker:
                results.append(request_id)
                await asyncio.sleep(0.01)

        # Run 10 concurrent requests
        await asyncio.gather(*[make_request(i) for i in range(10)])

        assert len(results) == 10
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_failures(self):
        """Test circuit breaker with concurrent failures."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker("test-service", config=config)
        errors = []

        async def make_failing_request(request_id: int):
            try:
                async with breaker:
                    await asyncio.sleep(0.01)
                    raise ValueError(f"Error {request_id}")
            except ValueError as e:
                errors.append(str(e))

        # Run 5 concurrent failing requests
        await asyncio.gather(
            *[make_failing_request(i) for i in range(5)],
            return_exceptions=True,
        )

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count >= config.failure_threshold

    @pytest.mark.asyncio
    async def test_retry_with_zero_delay(self):
        """Test retry with zero base delay."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2, base_delay=0.0, jitter=False))
        async def fast_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("Error", status_code=500)
            return "success"

        result = await fast_retry()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_config_edge_values(self):
        """Test circuit breaker with edge case configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            reset_timeout=0.01,
        )
        breaker = CircuitBreaker("test-service", config=config)

        # Single failure should open circuit
        try:
            async with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN

        # Wait for reset
        await asyncio.sleep(0.02)

        # Single success should close circuit
        async with breaker:
            pass

        assert breaker.state == CircuitState.CLOSED

    def test_retry_config_validation(self):
        """Test RetryConfig with various valid configurations."""
        # Test minimum values
        config = RetryConfig(
            max_retries=0,
            base_delay=0.0,
            max_delay=0.0,
            exponential_base=1.0,
            jitter_factor=0.0,
        )
        assert config.calculate_delay(0) == 0.0

        # Test large values
        config = RetryConfig(
            max_retries=100,
            base_delay=1000.0,
            max_delay=10000.0,
            exponential_base=10.0,
            jitter_factor=1.0,
        )
        delay = config.calculate_delay(0)
        assert delay >= 0

    def test_circuit_breaker_status_serialization(self):
        """Test that circuit breaker status can be serialized."""
        import json

        breaker = CircuitBreaker("test-service")
        status = breaker.get_status()

        # Should be JSON serializable
        json_str = json.dumps(status)
        assert json_str is not None

        # Should deserialize correctly
        deserialized = json.loads(json_str)
        assert deserialized["service"] == "test-service"
        assert deserialized["state"] == "closed"
