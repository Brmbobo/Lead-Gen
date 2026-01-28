"""
Health check endpoints for Lead-Gen API.

Provides:
- Basic health check
- Readiness check (service availability)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
import structlog

from lead_gen.api.dependencies import (
    get_correlation_id,
    get_hunter_service_optional,
    get_openai_service_optional,
    get_places_service_optional,
    get_sheets_service_optional,
)
from lead_gen.api.schemas import (
    HealthResponse,
    HealthStatus,
    ReadinessResponse,
    ServiceHealth,
)


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

# Track application start time
_start_time = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns basic health status and uptime information.",
)
async def health_check(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        Basic health status with version and uptime
    """
    uptime = time.time() - _start_time

    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version="1.0.0",
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc),
        correlation_id=correlation_id,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Checks if all required services are available and ready.",
)
async def readiness_check(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> ReadinessResponse:
    """
    Readiness check endpoint.

    Checks availability of:
    - Google Places API
    - OpenAI API
    - Hunter.io API (optional)
    - Google Sheets API (optional)

    Returns:
        Readiness status with individual service health
    """
    services: list[ServiceHealth] = []
    overall_status = HealthStatus.HEALTHY
    all_ready = True

    # Check Google Places
    try:
        places_service = await get_places_service_optional()
        if places_service:
            services.append(ServiceHealth(
                name="google_places",
                status=HealthStatus.HEALTHY,
                message="Service configured",
            ))
        else:
            services.append(ServiceHealth(
                name="google_places",
                status=HealthStatus.UNHEALTHY,
                message="Service not configured",
            ))
            all_ready = False
            overall_status = HealthStatus.DEGRADED
    except Exception as e:
        services.append(ServiceHealth(
            name="google_places",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        ))
        all_ready = False
        overall_status = HealthStatus.DEGRADED

    # Check OpenAI
    try:
        openai_service = await get_openai_service_optional()
        if openai_service:
            services.append(ServiceHealth(
                name="openai",
                status=HealthStatus.HEALTHY,
                message="Service configured",
            ))
        else:
            services.append(ServiceHealth(
                name="openai",
                status=HealthStatus.UNHEALTHY,
                message="Service not configured",
            ))
            all_ready = False
            overall_status = HealthStatus.DEGRADED
    except Exception as e:
        services.append(ServiceHealth(
            name="openai",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        ))
        all_ready = False
        overall_status = HealthStatus.DEGRADED

    # Check Hunter (optional)
    try:
        hunter_service = await get_hunter_service_optional()
        if hunter_service:
            services.append(ServiceHealth(
                name="hunter",
                status=HealthStatus.HEALTHY,
                message="Service configured",
            ))
        else:
            services.append(ServiceHealth(
                name="hunter",
                status=HealthStatus.DEGRADED,
                message="Service not configured (optional)",
            ))
    except Exception as e:
        services.append(ServiceHealth(
            name="hunter",
            status=HealthStatus.DEGRADED,
            message=f"Optional service error: {e}",
        ))

    # Check Sheets (optional)
    try:
        sheets_service = await get_sheets_service_optional()
        if sheets_service:
            services.append(ServiceHealth(
                name="google_sheets",
                status=HealthStatus.HEALTHY,
                message="Service configured",
            ))
        else:
            services.append(ServiceHealth(
                name="google_sheets",
                status=HealthStatus.DEGRADED,
                message="Service not configured (optional)",
            ))
    except Exception as e:
        services.append(ServiceHealth(
            name="google_sheets",
            status=HealthStatus.DEGRADED,
            message=f"Optional service error: {e}",
        ))

    logger.info(
        "readiness_check_completed",
        ready=all_ready,
        status=overall_status.value,
        services_checked=len(services),
        correlation_id=correlation_id,
    )

    return ReadinessResponse(
        ready=all_ready,
        status=overall_status,
        services=services,
        timestamp=datetime.now(timezone.utc),
        correlation_id=correlation_id,
    )
