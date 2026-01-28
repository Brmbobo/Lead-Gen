"""
FastAPI dependency injection for Lead-Gen API.

Provides dependencies for:
- Service instances
- Settings access
- Request correlation
- Authentication (optional)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status
import structlog

from lead_gen.core.config import Settings, get_settings
from lead_gen.core.exceptions import ConfigurationError


logger = structlog.get_logger(__name__)


# Correlation ID dependency
async def get_correlation_id(
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> str:
    """
    Get or generate correlation ID for request tracking.

    Accepts X-Correlation-ID header or generates a new UUID.
    """
    return x_correlation_id or str(uuid4())


# Settings dependency
def get_app_settings() -> Settings:
    """Get application settings."""
    return get_settings()


# Optional API key authentication
async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    settings: Settings = Depends(get_app_settings),
) -> str | None:
    """
    Verify optional API key for protected endpoints.

    In production, this would validate against a database or secret store.
    For now, this is a placeholder that always passes.

    Returns:
        The API key if provided and valid, None if not required
    """
    # For development, API key is optional
    if settings.is_development:
        return x_api_key

    # In production, you would validate against stored keys
    # This is a placeholder - implement your auth logic here
    return x_api_key


# Service factory dependencies
class ServiceFactory:
    """
    Factory for creating service instances.

    Services are created lazily and cached for the application lifetime.
    """

    _places_service = None
    _hunter_service = None
    _openai_service = None
    _sheets_service = None

    @classmethod
    async def get_places_service(cls):
        """Get or create PlacesService instance."""
        if cls._places_service is None:
            try:
                from lead_gen.services.places_service import PlacesService
                cls._places_service = PlacesService()
            except ConfigurationError as e:
                logger.warning("places_service_not_available", error=str(e))
                return None
        return cls._places_service

    @classmethod
    async def get_hunter_service(cls):
        """Get or create HunterService instance."""
        if cls._hunter_service is None:
            try:
                from lead_gen.services.hunter_service import HunterService
                cls._hunter_service = HunterService()
            except ConfigurationError as e:
                logger.warning("hunter_service_not_available", error=str(e))
                return None
        return cls._hunter_service

    @classmethod
    async def get_openai_service(cls):
        """Get or create OpenAIService instance."""
        if cls._openai_service is None:
            try:
                from lead_gen.services.openai_service import OpenAIService
                cls._openai_service = OpenAIService()
            except ConfigurationError as e:
                logger.warning("openai_service_not_available", error=str(e))
                return None
        return cls._openai_service

    @classmethod
    async def get_sheets_service(cls):
        """Get or create SheetsService instance."""
        if cls._sheets_service is None:
            try:
                from lead_gen.services.sheets_service import SheetsService
                cls._sheets_service = SheetsService()
            except ConfigurationError as e:
                logger.warning("sheets_service_not_available", error=str(e))
                return None
        return cls._sheets_service

    @classmethod
    async def close_all(cls):
        """Close all service connections."""
        if cls._places_service:
            await cls._places_service.close()
            cls._places_service = None
        if cls._hunter_service:
            await cls._hunter_service.close()
            cls._hunter_service = None
        if cls._openai_service:
            await cls._openai_service.close()
            cls._openai_service = None
        if cls._sheets_service:
            # SheetsService may not have close method
            cls._sheets_service = None


# FastAPI dependencies for services
async def get_places_service():
    """Dependency for PlacesService."""
    service = await ServiceFactory.get_places_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Places service not configured",
        )
    return service


async def get_hunter_service():
    """Dependency for HunterService."""
    service = await ServiceFactory.get_hunter_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hunter service not configured",
        )
    return service


async def get_openai_service():
    """Dependency for OpenAIService."""
    service = await ServiceFactory.get_openai_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI service not configured",
        )
    return service


async def get_sheets_service():
    """Dependency for SheetsService."""
    service = await ServiceFactory.get_sheets_service()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sheets service not configured",
        )
    return service


# Optional service dependencies (don't raise if unavailable)
async def get_places_service_optional():
    """Optional dependency for PlacesService."""
    return await ServiceFactory.get_places_service()


async def get_hunter_service_optional():
    """Optional dependency for HunterService."""
    return await ServiceFactory.get_hunter_service()


async def get_openai_service_optional():
    """Optional dependency for OpenAIService."""
    return await ServiceFactory.get_openai_service()


async def get_sheets_service_optional():
    """Optional dependency for SheetsService."""
    return await ServiceFactory.get_sheets_service()


# In-memory lead storage (for demo - replace with database in production)
class LeadStore:
    """
    In-memory lead storage.

    This is a simple implementation for demonstration.
    In production, replace with a proper database.
    """

    def __init__(self):
        self._leads: dict[str, dict] = {}
        self._workflows: dict[str, dict] = {}

    def add_lead(self, lead_data: dict) -> str:
        """Add a lead and return its ID."""
        lead_id = lead_data.get("id") or str(uuid4())
        lead_data["id"] = lead_id
        self._leads[lead_id] = lead_data
        return lead_id

    def get_lead(self, lead_id: str) -> dict | None:
        """Get a lead by ID."""
        return self._leads.get(lead_id)

    def update_lead(self, lead_id: str, updates: dict) -> dict | None:
        """Update a lead and return the updated data."""
        if lead_id not in self._leads:
            return None
        self._leads[lead_id].update(updates)
        return self._leads[lead_id]

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead and return success status."""
        if lead_id in self._leads:
            del self._leads[lead_id]
            return True
        return False

    def list_leads(
        self,
        filters: dict | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """List leads with optional filtering."""
        leads = list(self._leads.values())

        # Apply filters
        if filters:
            if filters.get("status"):
                leads = [l for l in leads if l.get("status") == filters["status"]]
            if filters.get("source"):
                leads = [l for l in leads if l.get("source") == filters["source"]]
            if filters.get("business_type"):
                leads = [
                    l for l in leads
                    if filters["business_type"].lower() in l.get("business_type", "").lower()
                ]
            if filters.get("min_quality_score") is not None:
                leads = [
                    l for l in leads
                    if l.get("quality_score", 0) >= filters["min_quality_score"]
                ]
            if filters.get("has_email") is True:
                leads = [l for l in leads if l.get("email")]
            if filters.get("has_phone") is True:
                leads = [l for l in leads if l.get("phone")]
            if filters.get("search"):
                search = filters["search"].lower()
                leads = [
                    l for l in leads
                    if search in l.get("name", "").lower()
                    or search in l.get("email", "").lower()
                    or search in l.get("phone", "").lower()
                ]

        total = len(leads)
        return leads[offset:offset + limit], total

    def add_workflow(self, workflow_data: dict) -> str:
        """Add a workflow and return its ID."""
        workflow_id = workflow_data.get("id") or str(uuid4())
        workflow_data["id"] = workflow_id
        self._workflows[workflow_id] = workflow_data
        return workflow_id

    def get_workflow(self, workflow_id: str) -> dict | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[dict]:
        """List all workflows."""
        return list(self._workflows.values())


# Global lead store instance
_lead_store: LeadStore | None = None


def get_lead_store() -> LeadStore:
    """Get the global lead store instance."""
    global _lead_store
    if _lead_store is None:
        _lead_store = LeadStore()
    return _lead_store
