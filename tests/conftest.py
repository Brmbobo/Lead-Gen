"""
Pytest configuration and fixtures for Lead-Gen tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lead_gen.core.config import Settings, reload_settings
from lead_gen.models.lead import Lead, LeadSource, Location, BusinessMetrics
from lead_gen.models.outreach import OutreachMessage, MessageLanguage, MessageTone
from lead_gen.tools.base import ToolContext


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    with patch.dict("os.environ", {
        "GOOGLE_PLACES_API_KEY": "test-places-key",
        "OPENAI_API_KEY": "test-openai-key",
        "HUNTER_API_KEY": "test-hunter-key",
        "GOOGLE_SERVICE_ACCOUNT_BASE64": "eyJ0eXBlIjoidGVzdCJ9",
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "DEBUG",
    }):
        return reload_settings()


@pytest.fixture
def sample_lead() -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        id="test-lead-1",
        place_id="ChIJtest123",
        name="Zubná Ambulancia Dr. Novák",
        phone="+421901234567",
        website="https://www.zubar-novak.sk",
        location=Location(
            latitude=48.1486,
            longitude=17.1077,
            formatted_address="Hlavná 123, 811 01 Bratislava",
            city="Bratislava",
            country="Slovakia",
            country_code="SK",
        ),
        business_type="dentist",
        categories=["dentist", "health"],
        metrics=BusinessMetrics(
            rating=4.8,
            review_count=125,
            price_level=2,
        ),
        source=LeadSource.GOOGLE_PLACES,
    )


@pytest.fixture
def sample_leads(sample_lead: Lead) -> list[Lead]:
    """Create multiple sample leads."""
    leads = [sample_lead]

    # Add more leads
    for i in range(2, 6):
        leads.append(Lead(
            id=f"test-lead-{i}",
            place_id=f"ChIJtest{i}",
            name=f"Test Dentist {i}",
            phone=f"+4219012345{i:02d}",
            location=Location(
                latitude=48.1486 + i * 0.01,
                longitude=17.1077 + i * 0.01,
                city="Bratislava",
                country="Slovakia",
            ),
            business_type="dentist",
            metrics=BusinessMetrics(
                rating=4.0 + i * 0.1,
                review_count=50 + i * 10,
            ),
            source=LeadSource.GOOGLE_PLACES,
        ))

    return leads


@pytest.fixture
def sample_message() -> OutreachMessage:
    """Create a sample outreach message."""
    return OutreachMessage(
        id="test-msg-1",
        subject="Spolupráca pre Zubná Ambulancia Dr. Novák",
        body="Dobrý deň,\n\noslovujem Vás s ponukou...",
        language=MessageLanguage.SLOVAK,
        tone=MessageTone.PROFESSIONAL,
        lead_id="test-lead-1",
        generation_model="gpt-4o-mini",
        generation_tokens=150,
        generation_cost_usd=0.0001,
    )


@pytest.fixture
def tool_context() -> ToolContext:
    """Create a tool context for testing."""
    return ToolContext(
        correlation_id="test-correlation-id",
        dry_run=False,
    )


@pytest.fixture
def mock_places_response() -> dict:
    """Create a mock Google Places API response."""
    return {
        "places": [
            {
                "id": "ChIJtest123",
                "displayName": {"text": "Test Dentist"},
                "formattedAddress": "Test Address 123",
                "internationalPhoneNumber": "+421901234567",
                "websiteUri": "https://test.sk",
                "location": {"latitude": 48.1486, "longitude": 17.1077},
                "rating": 4.5,
                "userRatingCount": 100,
                "types": ["dentist"],
                "primaryType": "dentist",
            }
        ]
    }


@pytest.fixture
def mock_openai_response() -> dict:
    """Create a mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "SUBJECT: Test Subject\nBODY: Test body content",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }


@pytest.fixture
def mock_hunter_response() -> dict:
    """Create a mock Hunter.io API response."""
    return {
        "data": {
            "email": "test@example.sk",
            "score": 85,
            "first_name": "Test",
            "last_name": "User",
            "position": "Owner",
            "verification": {"status": "valid"},
        }
    }
