"""
Google Places API (New) service client.

Provides async access to Google Places API v1 for:
- Text search for businesses
- Place details retrieval
- Nearby search

Rate limited and with circuit breaker support.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
import structlog

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import APIError, ConfigurationError, RateLimitError
from lead_gen.core.rate_limiter import RateLimitConfig, get_rate_limiter
from lead_gen.core.retry import CircuitBreaker, RetryConfig, retry_with_backoff
from lead_gen.models.lead import (
    BusinessMetrics,
    Lead,
    LeadSource,
    Location,
    OpeningHours,
)

logger = structlog.get_logger(__name__)

# Google Places API v1 endpoints
PLACES_API_BASE = "https://places.googleapis.com/v1"
SEARCH_TEXT_URL = f"{PLACES_API_BASE}/places:searchText"
PLACE_DETAILS_URL = f"{PLACES_API_BASE}/places"
NEARBY_SEARCH_URL = f"{PLACES_API_BASE}/places:searchNearby"


@dataclass
class PlacesSearchResult:
    """Result from a Places API search."""

    places: list[Lead]
    next_page_token: str | None = None
    total_count: int = 0
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    search_query: str = ""
    search_location: str = ""
    api_response_time_ms: float = 0


class PlacesService:
    """
    Google Places API (New) service client.

    Provides async methods for searching and retrieving place data.
    Includes rate limiting, retry logic, and circuit breaker.

    Example:
        >>> service = PlacesService()
        >>> result = await service.search_text("zubár Bratislava", max_results=20)
        >>> for lead in result.places:
        ...     print(lead.name, lead.phone)
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Places service.

        Args:
            api_key: Google Places API key (defaults to settings)
            timeout: Request timeout in seconds
        """
        settings = get_settings()

        self.api_key = api_key or settings.get_google_places_key()
        if not self.api_key:
            raise ConfigurationError(
                "Google Places API key not configured",
                config_key="GOOGLE_PLACES_API_KEY",
            )

        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(service="google_places")

        # Configure rate limiter
        limiter = get_rate_limiter()
        limiter.add_service(
            "google_places",
            RateLimitConfig(requests_per_minute=settings.rate_limits.google_places),
        )

        logger.info(
            "places_service_initialized",
            timeout=timeout,
            rate_limit=settings.rate_limits.google_places,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "PlacesService":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @retry_with_backoff(
        config=RetryConfig(max_retries=3, base_delay=1.0),
    )
    async def search_text(
        self,
        query: str,
        location: str = "",
        radius_km: int = 50,
        max_results: int = 20,
        language: str = "sk",
        region: str = "sk",
        min_rating: float | None = None,
        open_now: bool = False,
        included_types: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> PlacesSearchResult:
        """
        Search for places using text query.

        Args:
            query: Search query (e.g., "zubár Bratislava")
            location: Location bias (e.g., "Bratislava, Slovakia")
            radius_km: Search radius in kilometers
            max_results: Maximum number of results (1-20)
            language: Language code for results
            region: Region code for bias
            min_rating: Minimum rating filter
            open_now: Only show places open now
            included_types: List of place types to include
            correlation_id: Request correlation ID

        Returns:
            PlacesSearchResult with list of leads
        """
        correlation_id = correlation_id or str(uuid4())
        max_results = min(max_results, 20)  # API limit

        # Build request
        request_body: dict[str, Any] = {
            "textQuery": f"{query} {location}".strip(),
            "maxResultCount": max_results,
            "languageCode": language,
            "regionCode": region,
        }

        # Location bias
        if location:
            request_body["locationBias"] = {
                "circle": {
                    "center": await self._geocode_location(location),
                    "radius": radius_km * 1000,  # Convert to meters
                }
            }

        # Filters
        if min_rating:
            request_body["minRating"] = min_rating
        if open_now:
            request_body["openNow"] = True
        if included_types:
            request_body["includedTypes"] = included_types

        # Field mask - specify which fields to return
        field_mask = [
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.nationalPhoneNumber",
            "places.internationalPhoneNumber",
            "places.websiteUri",
            "places.googleMapsUri",
            "places.location",
            "places.rating",
            "places.userRatingCount",
            "places.priceLevel",
            "places.types",
            "places.primaryType",
            "places.regularOpeningHours",
        ]

        # Rate limit
        limiter = get_rate_limiter()
        await limiter.acquire("google_places")

        # Make request
        start_time = datetime.now(timezone.utc)

        async with self._circuit_breaker:
            client = await self._get_client()

            try:
                response = await client.post(
                    SEARCH_TEXT_URL,
                    json=request_body,
                    headers={"X-Goog-FieldMask": ",".join(field_mask)},
                )

                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                if response.status_code == 429:
                    raise RateLimitError(
                        "Google Places API rate limit exceeded",
                        service="google_places",
                        retry_after_seconds=60,
                    )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise APIError(
                        f"Google Places API error: {response.status_code}",
                        status_code=response.status_code,
                        response_body=str(error_data),
                        service="google_places",
                        operation="search_text",
                    )

                data = response.json()

            except httpx.RequestError as e:
                raise APIError(
                    f"Network error calling Google Places API: {e}",
                    service="google_places",
                    operation="search_text",
                    cause=e,
                )

        # Parse results
        places_data = data.get("places", [])
        leads = [self._parse_place(p, correlation_id) for p in places_data]

        logger.info(
            "places_search_completed",
            query=query,
            location=location,
            results_count=len(leads),
            response_time_ms=response_time,
            correlation_id=correlation_id,
        )

        return PlacesSearchResult(
            places=leads,
            next_page_token=data.get("nextPageToken"),
            total_count=len(leads),
            correlation_id=correlation_id,
            search_query=query,
            search_location=location,
            api_response_time_ms=response_time,
        )

    async def get_place_details(
        self,
        place_id: str,
        correlation_id: str | None = None,
    ) -> Lead | None:
        """
        Get detailed information for a specific place.

        Args:
            place_id: Google Place ID
            correlation_id: Request correlation ID

        Returns:
            Lead with full details or None if not found
        """
        correlation_id = correlation_id or str(uuid4())

        field_mask = [
            "id",
            "displayName",
            "formattedAddress",
            "nationalPhoneNumber",
            "internationalPhoneNumber",
            "websiteUri",
            "googleMapsUri",
            "location",
            "rating",
            "userRatingCount",
            "priceLevel",
            "types",
            "primaryType",
            "regularOpeningHours",
            "addressComponents",
            "reviews",
        ]

        # Rate limit
        limiter = get_rate_limiter()
        await limiter.acquire("google_places")

        async with self._circuit_breaker:
            client = await self._get_client()

            try:
                response = await client.get(
                    f"{PLACE_DETAILS_URL}/{place_id}",
                    headers={"X-Goog-FieldMask": ",".join(field_mask)},
                )

                if response.status_code == 404:
                    return None

                if response.status_code != 200:
                    raise APIError(
                        f"Google Places API error: {response.status_code}",
                        status_code=response.status_code,
                        service="google_places",
                        operation="get_place_details",
                    )

                data = response.json()

            except httpx.RequestError as e:
                raise APIError(
                    f"Network error calling Google Places API: {e}",
                    service="google_places",
                    operation="get_place_details",
                    cause=e,
                )

        return self._parse_place(data, correlation_id)

    def _parse_place(self, data: dict[str, Any], correlation_id: str) -> Lead:
        """Parse Google Places API response into Lead model."""
        # Location
        location_data = data.get("location", {})
        location = None
        if location_data:
            location = Location(
                latitude=location_data.get("latitude", 0),
                longitude=location_data.get("longitude", 0),
                formatted_address=data.get("formattedAddress", ""),
            )

        # Metrics
        metrics = BusinessMetrics(
            rating=data.get("rating"),
            review_count=data.get("userRatingCount", 0),
            price_level=data.get("priceLevel"),
            user_ratings_total=data.get("userRatingCount", 0),
        )

        # Opening hours
        opening_hours = None
        hours_data = data.get("regularOpeningHours", {})
        if hours_data:
            weekday_texts = hours_data.get("weekdayDescriptions", [])
            opening_hours = OpeningHours(
                monday=weekday_texts[0] if len(weekday_texts) > 0 else "",
                tuesday=weekday_texts[1] if len(weekday_texts) > 1 else "",
                wednesday=weekday_texts[2] if len(weekday_texts) > 2 else "",
                thursday=weekday_texts[3] if len(weekday_texts) > 3 else "",
                friday=weekday_texts[4] if len(weekday_texts) > 4 else "",
                saturday=weekday_texts[5] if len(weekday_texts) > 5 else "",
                sunday=weekday_texts[6] if len(weekday_texts) > 6 else "",
            )

        # Get display name
        display_name = data.get("displayName", {})
        name = display_name.get("text", "") if isinstance(display_name, dict) else str(display_name)

        # Phone - prefer international format
        phone = data.get("internationalPhoneNumber", "") or data.get("nationalPhoneNumber", "")

        # Website
        website = data.get("websiteUri")

        # Types/categories
        types = data.get("types", [])
        primary_type = data.get("primaryType", "")

        return Lead(
            place_id=data.get("id", ""),
            name=name,
            phone=phone,
            website=website,
            location=location,
            business_type=primary_type,
            categories=types,
            metrics=metrics,
            opening_hours=opening_hours,
            source=LeadSource.GOOGLE_PLACES,
            source_url=data.get("googleMapsUri"),
            correlation_id=correlation_id,
        )

    async def _geocode_location(self, location: str) -> dict[str, float]:
        """
        Convert location string to coordinates.

        This is a simplified implementation. In production,
        use Google Geocoding API for accurate results.
        """
        # Default to Bratislava coordinates for Slovak locations
        defaults = {
            "bratislava": {"latitude": 48.1486, "longitude": 17.1077},
            "košice": {"latitude": 48.7164, "longitude": 21.2611},
            "prešov": {"latitude": 48.9982, "longitude": 21.2393},
            "žilina": {"latitude": 49.2231, "longitude": 18.7394},
            "nitra": {"latitude": 48.3069, "longitude": 18.0864},
            "banská bystrica": {"latitude": 48.7360, "longitude": 19.1461},
            "trnava": {"latitude": 48.3774, "longitude": 17.5883},
            "trenčín": {"latitude": 48.8945, "longitude": 18.0444},
            # Czech
            "praha": {"latitude": 50.0755, "longitude": 14.4378},
            "brno": {"latitude": 49.1951, "longitude": 16.6068},
            # Austria
            "wien": {"latitude": 48.2082, "longitude": 16.3738},
            "vienna": {"latitude": 48.2082, "longitude": 16.3738},
        }

        location_lower = location.lower()
        for city, coords in defaults.items():
            if city in location_lower:
                return coords

        # Default to Bratislava
        return {"latitude": 48.1486, "longitude": 17.1077}


# Factory function for creating service
async def create_places_service(api_key: str | None = None) -> PlacesService:
    """Create and initialize a PlacesService instance."""
    return PlacesService(api_key=api_key)
