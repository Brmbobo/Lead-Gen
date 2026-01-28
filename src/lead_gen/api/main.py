"""
FastAPI application factory for Lead-Gen.

Creates and configures the FastAPI application with:
- API routes
- Middleware
- OpenAPI documentation
- Lifespan management
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import structlog

from lead_gen.api.dependencies import ServiceFactory
from lead_gen.api.middleware import setup_middleware
from lead_gen.api.routes import (
    health_router,
    leads_router,
    settings_router,
    workflows_router,
)
from lead_gen.core.config import get_settings


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events:
    - Startup: Initialize services, log startup
    - Shutdown: Close service connections, cleanup
    """
    # Startup
    settings = get_settings()
    logger.info(
        "application_starting",
        environment=settings.environment.value,
        log_level=settings.log_level.value,
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await ServiceFactory.close_all()
    logger.info("application_shutdown_complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Lead-Gen API",
        description="""
Enterprise-grade lead generation platform with AI-powered outreach.

## Features

- **Lead Management**: CRUD operations for business leads
- **Workflow Automation**: Configurable multi-step pipelines
- **Email Enrichment**: Integration with Hunter.io
- **AI Outreach**: OpenAI-powered message generation
- **Export**: CSV, JSON, and Google Sheets export

## Authentication

API key authentication via `X-API-Key` header (optional in development).

## Rate Limiting

All endpoints are rate limited. See settings for limits per service.

## GDPR Compliance

This API supports GDPR requirements including:
- Data subject access requests
- Right to erasure (delete endpoint)
- Data portability (export endpoint)
""",
        version="1.0.0",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Setup middleware (CORS, logging, error handling)
    setup_middleware(app)

    # Register API routes with /api/v1 prefix
    api_v1_prefix = "/api/v1"

    app.include_router(health_router, prefix=api_v1_prefix)
    app.include_router(leads_router, prefix=api_v1_prefix)
    app.include_router(workflows_router, prefix=api_v1_prefix)
    app.include_router(settings_router, prefix=api_v1_prefix)

    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authentication (optional in development)",
            },
            "CorrelationId": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Correlation-ID",
                "description": "Optional correlation ID for request tracking",
            },
        }

        # Add server URLs
        openapi_schema["servers"] = [
            {"url": "http://localhost:8000", "description": "Development server"},
        ]

        # Add tags metadata
        openapi_schema["tags"] = [
            {
                "name": "Health",
                "description": "Health check and readiness endpoints",
            },
            {
                "name": "Leads",
                "description": "Lead management operations",
            },
            {
                "name": "Workflows",
                "description": "Workflow execution and management",
            },
            {
                "name": "Settings",
                "description": "Application settings management",
            },
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    logger.info(
        "application_created",
        title=app.title,
        version=app.version,
        docs_url=app.docs_url,
    )

    return app


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    """
    Get cached FastAPI application instance.

    Use this for testing or when you need the same app instance.
    """
    return create_app()


# Root endpoint for basic info
def add_root_endpoint(app: FastAPI) -> None:
    """Add root endpoint with API info."""

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "Lead-Gen API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/v1/health",
        }


# Create default application instance
app = create_app()
add_root_endpoint(app)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "lead_gen.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.value.lower(),
    )
