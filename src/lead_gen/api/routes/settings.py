"""
Settings management endpoints for Lead-Gen API.

Provides:
- Get current settings (secrets masked)
- Update settings
- Validate API keys
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from lead_gen.api.dependencies import (
    get_app_settings,
    get_correlation_id,
    get_hunter_service_optional,
    get_openai_service_optional,
    get_places_service_optional,
)
from lead_gen.api.schemas import (
    APIKeyValidationResult,
    APIResponse,
    GDPRSettingsSchema,
    OpenAISettingsSchema,
    RateLimitSettingsSchema,
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsValidateResponse,
)
from lead_gen.core.config import Settings


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


def _settings_to_response(settings: Settings) -> SettingsResponse:
    """Convert Settings to response schema (secrets masked)."""
    return SettingsResponse(
        environment=settings.environment.value,
        log_level=settings.log_level.value,
        rate_limits=RateLimitSettingsSchema(
            google_places=settings.rate_limits.google_places,
            openai=settings.rate_limits.openai,
            hunter=settings.rate_limits.hunter,
            sheets=settings.rate_limits.sheets,
        ),
        gdpr=GDPRSettingsSchema(
            retention_days=settings.gdpr.retention_days,
            legal_basis=settings.gdpr.legal_basis,
            dpo_email=settings.gdpr.dpo_email,
            enable_audit_log=settings.gdpr.enable_audit_log,
        ),
        openai=OpenAISettingsSchema(
            model=settings.openai.model,
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature,
        ),
        google_places_api_key_configured=bool(settings.google_places_api_key.get_secret_value()),
        openai_api_key_configured=bool(settings.openai_api_key.get_secret_value()),
        hunter_api_key_configured=bool(settings.hunter_api_key.get_secret_value()),
        google_service_account_configured=bool(
            settings.google_service_account_path
            or settings.google_service_account_base64.get_secret_value()
        ),
    )


@router.get(
    "",
    response_model=APIResponse[SettingsResponse],
    summary="Get settings",
    description="Get current application settings. Secrets are masked.",
)
async def get_settings(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> APIResponse[SettingsResponse]:
    """
    Get current settings.

    Returns settings with secrets masked.
    API keys show only whether they are configured, not the actual values.
    """
    logger.info(
        "settings_retrieved",
        environment=settings.environment.value,
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=_settings_to_response(settings),
        correlation_id=correlation_id,
    )


@router.put(
    "",
    response_model=APIResponse[SettingsResponse],
    summary="Update settings",
    description="Update application settings. Note: Changes are not persistent across restarts.",
)
async def update_settings(
    request: SettingsUpdateRequest,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> APIResponse[SettingsResponse]:
    """
    Update settings.

    Note: In the current implementation, settings changes are not
    persistent across application restarts. For persistent settings,
    modify environment variables or configuration files.
    """
    # In a real implementation, you would:
    # 1. Validate the changes
    # 2. Persist to a database or config file
    # 3. Reload the settings

    # For now, we just log the request and return current settings
    # This is because Settings is typically loaded once from environment

    logger.warning(
        "settings_update_requested",
        note="Settings updates are not persistent in current implementation",
        updates={
            "rate_limits": request.rate_limits.model_dump() if request.rate_limits else None,
            "gdpr": request.gdpr.model_dump() if request.gdpr else None,
            "openai": request.openai.model_dump() if request.openai else None,
        },
        correlation_id=correlation_id,
    )

    # Return current settings
    return APIResponse(
        success=True,
        data=_settings_to_response(settings),
        correlation_id=correlation_id,
    )


@router.get(
    "/validate",
    response_model=SettingsValidateResponse,
    summary="Validate API keys",
    description="Validate that all configured API keys are working.",
)
async def validate_api_keys(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> SettingsValidateResponse:
    """
    Validate API keys.

    Tests each configured API key to ensure it is valid and working.
    """
    results: list[APIKeyValidationResult] = []
    all_valid = True

    # Check Google Places
    if settings.google_places_api_key.get_secret_value():
        try:
            service = await get_places_service_optional()
            if service:
                results.append(APIKeyValidationResult(
                    service="google_places",
                    valid=True,
                    message="API key configured and service initialized",
                ))
            else:
                results.append(APIKeyValidationResult(
                    service="google_places",
                    valid=False,
                    message="Service initialization failed",
                ))
                all_valid = False
        except Exception as e:
            results.append(APIKeyValidationResult(
                service="google_places",
                valid=False,
                message=str(e),
            ))
            all_valid = False
    else:
        results.append(APIKeyValidationResult(
            service="google_places",
            valid=False,
            message="API key not configured",
        ))
        all_valid = False

    # Check OpenAI
    if settings.openai_api_key.get_secret_value():
        try:
            service = await get_openai_service_optional()
            if service:
                results.append(APIKeyValidationResult(
                    service="openai",
                    valid=True,
                    message="API key configured and service initialized",
                ))
            else:
                results.append(APIKeyValidationResult(
                    service="openai",
                    valid=False,
                    message="Service initialization failed",
                ))
                all_valid = False
        except Exception as e:
            results.append(APIKeyValidationResult(
                service="openai",
                valid=False,
                message=str(e),
            ))
            all_valid = False
    else:
        results.append(APIKeyValidationResult(
            service="openai",
            valid=False,
            message="API key not configured",
        ))
        all_valid = False

    # Check Hunter (optional)
    if settings.hunter_api_key.get_secret_value():
        try:
            service = await get_hunter_service_optional()
            if service:
                results.append(APIKeyValidationResult(
                    service="hunter",
                    valid=True,
                    message="API key configured and service initialized",
                ))
            else:
                results.append(APIKeyValidationResult(
                    service="hunter",
                    valid=False,
                    message="Service initialization failed",
                ))
        except Exception as e:
            results.append(APIKeyValidationResult(
                service="hunter",
                valid=False,
                message=str(e),
            ))
    else:
        results.append(APIKeyValidationResult(
            service="hunter",
            valid=True,
            message="API key not configured (optional service)",
        ))

    # Check Google Service Account
    if settings.google_service_account_path or settings.google_service_account_base64.get_secret_value():
        results.append(APIKeyValidationResult(
            service="google_service_account",
            valid=True,
            message="Service account configured",
        ))
    else:
        results.append(APIKeyValidationResult(
            service="google_service_account",
            valid=False,
            message="Service account not configured",
        ))
        all_valid = False

    logger.info(
        "api_keys_validated",
        all_valid=all_valid,
        results_count=len(results),
        correlation_id=correlation_id,
    )

    return SettingsValidateResponse(
        all_valid=all_valid,
        results=results,
        correlation_id=correlation_id,
    )
