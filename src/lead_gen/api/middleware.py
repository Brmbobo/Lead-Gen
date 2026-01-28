"""
FastAPI middleware for Lead-Gen API.

Provides:
- CORS configuration
- Request ID middleware
- Structured logging
- Error handling
"""

from __future__ import annotations

import time
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import (
    APIError,
    ConfigurationError,
    GDPRError,
    LeadGenError,
    RateLimitError,
    SecurityError,
    ValidationError,
)


logger = structlog.get_logger(__name__)


def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware.

    Allows requests from frontend origins in development.
    In production, restrict to specific domains.
    """
    settings = get_settings()

    # Development origins
    dev_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Production would use environment-specific origins
    origins = dev_origins if settings.is_development else []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Request-ID"],
    )


class RequestContextMiddleware:
    """
    Middleware for request context management.

    Adds:
    - Request ID generation
    - Correlation ID handling
    - Request timing
    - Structured logging
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = str(uuid4())

        # Extract correlation ID from headers
        correlation_id = None
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"x-correlation-id":
                correlation_id = header_value.decode()
                break

        if not correlation_id:
            correlation_id = request_id

        # Store in scope for access in request handlers
        scope["state"] = scope.get("state", {})
        scope["state"]["request_id"] = request_id
        scope["state"]["correlation_id"] = correlation_id

        # Start timing
        start_time = time.perf_counter()

        # Modified send to add headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.append((b"x-correlation-id", correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        # Log request
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        logger.info(
            "request_started",
            method=method,
            path=path,
            request_id=request_id,
            correlation_id=correlation_id,
        )

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Log completion
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "request_completed",
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                correlation_id=correlation_id,
            )


def configure_exception_handlers(app: FastAPI) -> None:
    """Configure custom exception handlers."""

    @app.exception_handler(LeadGenError)
    async def leadgen_error_handler(request: Request, exc: LeadGenError) -> JSONResponse:
        """Handle all Lead-Gen custom exceptions."""

        # Get correlation ID from request state
        correlation_id = getattr(request.state, "correlation_id", None)

        # Map exception types to HTTP status codes
        status_code = 500
        error_code = "internal_error"

        if isinstance(exc, ValidationError):
            status_code = 400
            error_code = "validation_error"
        elif isinstance(exc, ConfigurationError):
            status_code = 503
            error_code = "configuration_error"
        elif isinstance(exc, RateLimitError):
            status_code = 429
            error_code = "rate_limit_exceeded"
        elif isinstance(exc, APIError):
            status_code = exc.status_code or 502
            error_code = "external_api_error"
        elif isinstance(exc, GDPRError):
            status_code = 403
            error_code = "gdpr_violation"
        elif isinstance(exc, SecurityError):
            status_code = 403
            error_code = "security_error"

        # Log error
        logger.error(
            "request_error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            error_code=error_code,
            status_code=status_code,
            correlation_id=correlation_id,
            error_id=exc.context.error_id,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": exc.message,
                "error_code": error_code,
                "details": exc.context.to_dict() if exc.context else None,
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""

        correlation_id = getattr(request.state, "correlation_id", None)

        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            correlation_id=correlation_id,
        )

        # Don't expose internal errors in production
        settings = get_settings()
        message = str(exc) if settings.is_development else "An internal error occurred"

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": message,
                "error_code": "internal_error",
                "correlation_id": correlation_id,
            },
        )


def configure_logging() -> None:
    """Configure structured logging with structlog."""
    import logging

    settings = get_settings()

    # Map log level string to Python logging level
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = log_level_map.get(settings.log_level.value, logging.INFO)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""

    # Configure logging first
    configure_logging()

    # Add CORS
    configure_cors(app)

    # Add request context middleware
    app.add_middleware(RequestContextMiddleware)

    # Add exception handlers
    configure_exception_handlers(app)
