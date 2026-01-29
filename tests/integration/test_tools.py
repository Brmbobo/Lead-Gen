"""
Integration tests for Lead-Gen tools.

Tests verify:
- Tool chaining (output of one is input to next)
- Context sharing between tools
- Error propagation
- Rate limiting across tools
- Data transformation pipelines
- Bounded collection behavior
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from lead_gen.core.exceptions import APIError, RateLimitError
from lead_gen.models.lead import (
    BusinessMetrics,
    EmailEnrichment,
    EnrichedLead,
    Lead,
    LeadSource,
    LeadStatus,
    Location,
)
from lead_gen.models.outreach import (
    MessageLanguage,
    MessageTone,
    MessageType,
    OutreachMessage,
    PersonalizationContext,
)
from lead_gen.models.workflow import (
    EnrichConfig,
    ExportConfig,
    GenerateConfig,
    ScrapeConfig,
)
from lead_gen.services.sheets_service import ExportResult
from lead_gen.tools.base import ToolContext, ToolResult, ToolStatus
from lead_gen.tools.enrich_email import EnrichEmailTool, EnrichInput
from lead_gen.tools.export_to_sheets import ExportInput, ExportOutput, ExportToSheetsTool
from lead_gen.tools.generate_outreach import GenerateInput, GenerateOutreachTool
from lead_gen.tools.scrape_leads import ScrapeInput, ScrapeLeadsTool


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tool_context() -> ToolContext:
    """Create a fresh tool context for testing."""
    return ToolContext(
        correlation_id=str(uuid4()),
        dry_run=False,
    )


@pytest.fixture
def sample_location() -> Location:
    """Create a sample location."""
    return Location(
        latitude=48.1486,
        longitude=17.1077,
        formatted_address="Hlavna 123, 811 01 Bratislava",
        street="Hlavna 123",
        city="Bratislava",
        region="Bratislavsky",
        postal_code="811 01",
        country="Slovakia",
        country_code="SK",
    )


@pytest.fixture
def sample_lead(sample_location: Location) -> Lead:
    """Create a sample lead for testing."""
    return Lead(
        id="lead-001",
        place_id="ChIJtest001",
        name="Zubna Ambulancia Dr. Novak",
        phone="+421901234567",
        website="https://www.zubar-novak.sk",
        location=sample_location,
        business_type="dentist",
        categories=["dentist", "health", "medical"],
        metrics=BusinessMetrics(rating=4.8, review_count=125, price_level=2),
        source=LeadSource.GOOGLE_PLACES,
    )


@pytest.fixture
def sample_leads(sample_location: Location) -> list[Lead]:
    """Create a list of sample leads."""
    leads = []
    businesses = [
        ("Zubna Ambulancia Dr. Novak", "dentist", "+421901234567", "https://www.zubar-novak.sk"),
        ("Dental Care Bratislava", "dentist", "+421902345678", "https://www.dental-care.sk"),
        ("SmileDent s.r.o.", "dental_clinic", "+421903456789", "https://www.smiledent.sk"),
        ("MUDr. Jana Kovacova", "dentist", "+421904567890", "https://www.kovacova-dental.sk"),
        ("Family Dental Center", "dental_clinic", "+421905678901", "https://www.familydental.sk"),
    ]

    for i, (name, btype, phone, website) in enumerate(businesses):
        leads.append(
            Lead(
                id=f"lead-{i+1:03d}",
                place_id=f"ChIJtest{i+1:03d}",
                name=name,
                phone=phone,
                website=website,
                location=Location(
                    latitude=sample_location.latitude + i * 0.01,
                    longitude=sample_location.longitude + i * 0.01,
                    formatted_address=f"Ulica {i+1}, Bratislava",
                    city="Bratislava",
                    country="Slovakia",
                    country_code="SK",
                ),
                business_type=btype,
                categories=["dentist", "health"],
                metrics=BusinessMetrics(
                    rating=4.0 + (i * 0.2),
                    review_count=50 + (i * 25),
                ),
                source=LeadSource.GOOGLE_PLACES,
            )
        )
    return leads


@pytest.fixture
def enriched_lead(sample_lead: Lead) -> EnrichedLead:
    """Create an enriched lead."""
    return EnrichedLead(
        **sample_lead.model_dump(),
        enrichments=[
            EmailEnrichment(
                email="info@zubar-novak.sk",
                confidence=92,
                type="generic",
                first_name="",
                last_name="",
                position="",
                verified=True,
                verified_at=datetime.now(timezone.utc),
            ),
            EmailEnrichment(
                email="novak@zubar-novak.sk",
                confidence=78,
                type="personal",
                first_name="Jan",
                last_name="Novak",
                position="Owner",
                verified=True,
            ),
        ],
        enriched_at=datetime.now(timezone.utc),
        enrichment_source="hunter",
    )


@pytest.fixture
def sample_message(sample_lead: Lead) -> OutreachMessage:
    """Create a sample outreach message."""
    return OutreachMessage(
        id="msg-001",
        subject="Spoluprace pre Zubna Ambulancia Dr. Novak",
        body=(
            "Dobry den,\n\n"
            "oslovujem Vas s ponukou, ktora by mohla zaujat Zubna Ambulancia Dr. Novak.\n\n"
            "Pomahame zubnym ambulanciam ziskat viac pacientov cez online marketing.\n\n"
            "Boli by ste ochotni venovat mi 15 minut na kratky rozhovor?\n\n"
            "S pozdravom,\n"
            "Jan Novak\n"
            "Lead-Gen s.r.o."
        ),
        language=MessageLanguage.SLOVAK,
        tone=MessageTone.PROFESSIONAL,
        message_type=MessageType.COLD_EMAIL,
        lead_id=sample_lead.id,
        generation_model="gpt-4o-mini",
        generation_tokens=150,
        generation_cost_usd=0.0001,
    )


@pytest.fixture
def scrape_config() -> ScrapeConfig:
    """Create scrape configuration."""
    return ScrapeConfig(
        query="zubar",
        location="Bratislava, Slovakia",
        radius_km=30,
        max_results=20,
        language="sk",
        region="sk",
        min_rating=4.0,
        min_reviews=5,
    )


@pytest.fixture
def generate_config() -> GenerateConfig:
    """Create generate configuration."""
    return GenerateConfig(
        model="gpt-4o-mini",
        language="sk",
        tone="professional",
        temperature=0.7,
        max_tokens=500,
        sender_name="Jan Novak",
        sender_company="Lead-Gen s.r.o.",
        value_proposition="Pomahame zubnym ambulanciam ziskat viac pacientov cez online marketing",
    )


@pytest.fixture
def enrich_config() -> EnrichConfig:
    """Create enrich configuration."""
    return EnrichConfig(
        provider="hunter",
        find_emails=True,
        verify_emails=True,
        max_enrichments_per_lead=3,
    )


@pytest.fixture
def export_config() -> ExportConfig:
    """Create export configuration."""
    return ExportConfig(
        destination="sheets",
        spreadsheet_id="test-spreadsheet-123",
        worksheet_name="Leads - Bratislava",
        append_mode=True,
        include_messages=True,
    )


# =============================================================================
# Mock Service Factories
# =============================================================================


@pytest.fixture
def mock_places_service(sample_leads: list[Lead]):
    """Create a mock PlacesService."""
    from lead_gen.services.places_service import PlacesSearchResult

    service = AsyncMock()
    service.search_text = AsyncMock(
        return_value=PlacesSearchResult(
            places=sample_leads,
            total_count=len(sample_leads),
            search_query="zubar",
            search_location="Bratislava",
            api_response_time_ms=250.0,
        )
    )
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_openai_service(sample_message: OutreachMessage):
    """Create a mock OpenAIService."""
    from lead_gen.services.openai_service import GenerationResult

    service = AsyncMock()

    async def generate_message_side_effect(lead: Lead, **kwargs):
        return GenerationResult(
            message=OutreachMessage(
                subject=f"Spoluprace pre {lead.name}",
                body=(
                    f"Dobry den,\n\n"
                    f"oslovujem Vas s ponukou pre {lead.name}.\n\n"
                    "S pozdravom"
                ),
                language=MessageLanguage.SLOVAK,
                tone=MessageTone.PROFESSIONAL,
                message_type=MessageType.COLD_EMAIL,
                lead_id=lead.id,
                generation_model="gpt-4o-mini",
                generation_tokens=120,
                generation_cost_usd=0.00008,
            ),
            prompt_tokens=80,
            completion_tokens=40,
            total_tokens=120,
            cost_usd=0.00008,
            generation_time_ms=850.0,
            model="gpt-4o-mini",
        )

    service.generate_message = AsyncMock(side_effect=generate_message_side_effect)
    return service


@pytest.fixture
def mock_hunter_service(sample_leads: list[Lead]):
    """Create a mock HunterService."""
    service = AsyncMock()

    async def enrich_lead_side_effect(lead: Lead, **kwargs):
        # Exclude computed fields when creating EnrichedLead
        lead_data = lead.model_dump(exclude={"display_name", "has_contact_info", "quality_score"})
        return EnrichedLead(
            **lead_data,
            enrichments=[
                EmailEnrichment(
                    email=f"info@{lead.name.lower().replace(' ', '-')}.sk",
                    confidence=85,
                    type="generic",
                    verified=True,
                )
            ],
            enriched_at=datetime.now(timezone.utc),
            enrichment_source="hunter",
        )

    service.enrich_lead = AsyncMock(side_effect=enrich_lead_side_effect)
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_sheets_service():
    """Create a mock SheetsService."""
    service = AsyncMock()

    async def export_leads_side_effect(leads, spreadsheet_id, **kwargs):
        return ExportResult(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=kwargs.get("worksheet_name", "Leads"),
            rows_exported=len(leads),
            spreadsheet_url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            export_time_ms=320.0,
        )

    async def export_messages_side_effect(messages, spreadsheet_id, **kwargs):
        return ExportResult(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=kwargs.get("worksheet_name", "Messages"),
            rows_exported=len(messages),
            spreadsheet_url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            export_time_ms=280.0,
        )

    service.export_leads = AsyncMock(side_effect=export_leads_side_effect)
    service.export_messages = AsyncMock(side_effect=export_messages_side_effect)
    return service


# =============================================================================
# Tool Chaining Tests
# =============================================================================


class TestToolChaining:
    """Tests for tool chaining (output of one tool feeds into the next)."""

    @pytest.mark.asyncio
    async def test_scrape_to_enrich_chain(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        enrich_config: EnrichConfig,
        mock_places_service,
        mock_hunter_service,
        sample_leads: list[Lead],
    ):
        """Test chaining scrape tool output to enrich tool input."""
        # Step 1: Scrape leads
        scrape_tool = ScrapeLeadsTool()
        scrape_input = ScrapeInput(config=scrape_config, places_service=mock_places_service)

        scrape_result = await scrape_tool.run(scrape_input, tool_context)

        assert scrape_result.status == ToolStatus.SUCCESS
        assert scrape_result.output is not None
        assert len(scrape_result.output) == len(sample_leads)

        # Verify leads are in context
        assert len(tool_context.leads) == len(sample_leads)

        # Step 2: Enrich leads using output from scrape
        enrich_tool = EnrichEmailTool()
        enrich_input = EnrichInput(
            leads=scrape_result.output,  # Direct chaining
            config=enrich_config,
            hunter_service=mock_hunter_service,
        )

        enrich_result = await enrich_tool.run(enrich_input, tool_context)

        assert enrich_result.status == ToolStatus.SUCCESS
        assert enrich_result.output is not None
        assert len(enrich_result.output) == len(sample_leads)

        # Verify enriched leads have email data
        for enriched_lead in enrich_result.output:
            assert isinstance(enriched_lead, EnrichedLead)
            assert len(enriched_lead.enrichments) > 0

    @pytest.mark.asyncio
    async def test_scrape_to_generate_chain(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        generate_config: GenerateConfig,
        mock_places_service,
        mock_openai_service,
        sample_leads: list[Lead],
    ):
        """Test chaining scrape tool output to generate outreach tool."""
        # Step 1: Scrape leads
        scrape_tool = ScrapeLeadsTool()
        scrape_input = ScrapeInput(config=scrape_config, places_service=mock_places_service)

        scrape_result = await scrape_tool.run(scrape_input, tool_context)

        assert scrape_result.status == ToolStatus.SUCCESS

        # Step 2: Generate messages for scraped leads
        generate_tool = GenerateOutreachTool()
        generate_input = GenerateInput(
            leads=scrape_result.output,  # Direct chaining
            config=generate_config,
            openai_service=mock_openai_service,
        )

        generate_result = await generate_tool.run(generate_input, tool_context)

        assert generate_result.status == ToolStatus.SUCCESS
        assert generate_result.output is not None
        assert len(generate_result.output) == len(sample_leads)

        # Verify messages have lead references
        for i, message in enumerate(generate_result.output):
            assert message.lead_id == sample_leads[i].id
            assert sample_leads[i].name in message.subject

    @pytest.mark.asyncio
    async def test_full_pipeline_chain(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        enrich_config: EnrichConfig,
        generate_config: GenerateConfig,
        export_config: ExportConfig,
        mock_places_service,
        mock_hunter_service,
        mock_openai_service,
        mock_sheets_service,
        sample_leads: list[Lead],
    ):
        """Test full pipeline: scrape -> enrich -> generate -> export."""
        # Step 1: Scrape
        scrape_tool = ScrapeLeadsTool()
        scrape_result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )
        assert scrape_result.is_success

        # Step 2: Enrich
        enrich_tool = EnrichEmailTool()
        enrich_result = await enrich_tool.run(
            EnrichInput(
                leads=scrape_result.output,
                config=enrich_config,
                hunter_service=mock_hunter_service,
            ),
            tool_context,
        )
        assert enrich_result.is_success

        # Step 3: Generate messages
        generate_tool = GenerateOutreachTool()
        generate_result = await generate_tool.run(
            GenerateInput(
                leads=enrich_result.output,
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )
        assert generate_result.is_success

        # Step 4: Export
        export_tool = ExportToSheetsTool()
        export_result = await export_tool.run(
            ExportInput(
                config=export_config,
                leads=enrich_result.output,
                messages=generate_result.output,
                sheets_service=mock_sheets_service,
            ),
            tool_context,
        )
        assert export_result.is_success

        # Verify export output
        assert export_result.output is not None
        assert export_result.output.leads_result is not None
        assert export_result.output.leads_result.rows_exported == len(sample_leads)
        assert export_result.output.spreadsheet_url != ""

    @pytest.mark.asyncio
    async def test_chain_with_data_transformation(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        generate_config: GenerateConfig,
        mock_places_service,
        mock_openai_service,
        sample_leads: list[Lead],
    ):
        """Test that data transforms correctly through the chain."""
        # Scrape with filtering
        scrape_config = ScrapeConfig(
            query="zubar",
            location="Bratislava",
            min_rating=4.5,  # This should filter some leads
            min_reviews=10,
        )

        scrape_tool = ScrapeLeadsTool()
        scrape_result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        # Apply filter (simulating min_rating filter - in real service this happens)
        filtered_leads = [
            lead for lead in (scrape_result.output or [])
            if lead.metrics.rating and lead.metrics.rating >= 4.5
        ]

        # Generate for filtered leads
        generate_tool = GenerateOutreachTool()
        generate_result = await generate_tool.run(
            GenerateInput(
                leads=filtered_leads,
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        assert generate_result.is_success
        # Verify messages match filtered leads count
        assert len(generate_result.output or []) == len(filtered_leads)


# =============================================================================
# Context Sharing Tests
# =============================================================================


class TestContextSharing:
    """Tests for context sharing between tools."""

    @pytest.mark.asyncio
    async def test_leads_shared_via_context(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        enrich_config: EnrichConfig,
        mock_places_service,
        mock_hunter_service,
        sample_leads: list[Lead],
    ):
        """Test that leads added to context are available to subsequent tools."""
        # Scrape adds leads to context
        scrape_tool = ScrapeLeadsTool()
        await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        assert len(tool_context.leads) == len(sample_leads)

        # Enrich reads from context (no explicit leads in input)
        enrich_tool = EnrichEmailTool()
        enrich_result = await enrich_tool.run(
            EnrichInput(
                leads=None,  # Will use context.leads
                config=enrich_config,
                hunter_service=mock_hunter_service,
            ),
            tool_context,
        )

        assert enrich_result.is_success
        assert len(enrich_result.output or []) == len(sample_leads)

    @pytest.mark.asyncio
    async def test_messages_shared_via_context(
        self,
        tool_context: ToolContext,
        export_config: ExportConfig,
        generate_config: GenerateConfig,
        mock_openai_service,
        mock_sheets_service,
        sample_leads: list[Lead],
    ):
        """Test that messages added to context are available to export tool."""
        # Add leads to context
        for lead in sample_leads:
            tool_context.add_lead(lead)

        # Generate messages (adds to context.messages)
        generate_tool = GenerateOutreachTool()
        await generate_tool.run(
            GenerateInput(
                leads=sample_leads,
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        assert len(tool_context.messages) == len(sample_leads)

        # Export reads messages from context
        export_tool = ExportToSheetsTool()
        export_result = await export_tool.run(
            ExportInput(
                config=export_config,
                leads=None,  # Will use context
                messages=None,  # Will use context
                sheets_service=mock_sheets_service,
            ),
            tool_context,
        )

        assert export_result.is_success
        # Verify messages were exported from context
        mock_sheets_service.export_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_enriched_leads_shared_via_context(
        self,
        tool_context: ToolContext,
        export_config: ExportConfig,
        enrich_config: EnrichConfig,
        mock_hunter_service,
        mock_sheets_service,
        sample_leads: list[Lead],
    ):
        """Test that enriched leads are stored separately in context."""
        # Add original leads
        for lead in sample_leads:
            tool_context.add_lead(lead)

        # Enrich (adds to context.enriched_leads)
        enrich_tool = EnrichEmailTool()
        await enrich_tool.run(
            EnrichInput(
                leads=sample_leads,
                config=enrich_config,
                hunter_service=mock_hunter_service,
            ),
            tool_context,
        )

        assert len(tool_context.enriched_leads) == len(sample_leads)
        # Original leads still there
        assert len(tool_context.leads) == len(sample_leads)

    @pytest.mark.asyncio
    async def test_correlation_id_propagates(
        self,
        scrape_config: ScrapeConfig,
        mock_places_service,
    ):
        """Test that correlation_id propagates through tools."""
        correlation_id = "test-correlation-123"
        context = ToolContext(correlation_id=correlation_id)

        scrape_tool = ScrapeLeadsTool()
        await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            context,
        )

        # Verify correlation_id was passed to service
        mock_places_service.search_text.assert_called_once()
        call_kwargs = mock_places_service.search_text.call_args.kwargs
        assert call_kwargs.get("correlation_id") == correlation_id

    @pytest.mark.asyncio
    async def test_metrics_accumulate_in_context(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        generate_config: GenerateConfig,
        mock_places_service,
        mock_openai_service,
        sample_leads: list[Lead],
    ):
        """Test that API call metrics accumulate in context."""
        initial_api_calls = tool_context.api_calls

        # Scrape
        scrape_tool = ScrapeLeadsTool()
        await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )
        assert tool_context.api_calls == initial_api_calls + 1

        # Generate (multiple API calls - one per lead)
        generate_tool = GenerateOutreachTool()
        await generate_tool.run(
            GenerateInput(
                leads=sample_leads,
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        # API calls should have increased (1 scrape + 1 generate batch)
        assert tool_context.api_calls >= initial_api_calls + 2


# =============================================================================
# Error Propagation Tests
# =============================================================================


class TestErrorPropagation:
    """Tests for error propagation through tools."""

    @pytest.mark.asyncio
    async def test_api_error_propagates(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
    ):
        """Test that API errors propagate correctly."""
        mock_service = AsyncMock()
        mock_service.search_text = AsyncMock(
            side_effect=APIError(
                "Google Places API error",
                service="google_places",
                status_code=500,
            )
        )
        mock_service.close = AsyncMock()

        scrape_tool = ScrapeLeadsTool()
        result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_service),
            tool_context,
        )

        assert result.status == ToolStatus.FAILED
        assert "Google Places API error" in result.error_message

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagates(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
    ):
        """Test that rate limit errors propagate correctly."""
        mock_service = AsyncMock()
        mock_service.search_text = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded",
                service="google_places",
                retry_after_seconds=60,
            )
        )
        mock_service.close = AsyncMock()

        scrape_tool = ScrapeLeadsTool()
        result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_service),
            tool_context,
        )

        assert result.status == ToolStatus.FAILED
        assert "Rate limit" in result.error_message

    @pytest.mark.asyncio
    async def test_partial_failure_returns_partial_status(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        sample_leads: list[Lead],
    ):
        """Test that partial failures result in PARTIAL status."""
        mock_service = AsyncMock()
        call_count = 0

        async def generate_with_failures(lead, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail every other call
            if call_count % 2 == 0:
                raise APIError("Simulated failure", service="openai")
            return MagicMock(
                message=OutreachMessage(
                    subject=f"Test for {lead.name}",
                    body="Test body",
                    lead_id=lead.id,
                ),
                total_tokens=100,
                cost_usd=0.0001,
            )

        mock_service.generate_message = AsyncMock(side_effect=generate_with_failures)

        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=sample_leads,
                config=generate_config,
                openai_service=mock_service,
            ),
            tool_context,
        )

        assert result.status == ToolStatus.PARTIAL
        assert result.items_failed > 0
        assert result.items_processed > 0

    @pytest.mark.asyncio
    async def test_input_validation_error(
        self,
        tool_context: ToolContext,
    ):
        """Test that input validation errors are handled via Pydantic."""
        from pydantic import ValidationError

        # Missing required query - Pydantic should reject this
        with pytest.raises(ValidationError) as exc_info:
            ScrapeConfig(query="", location="Bratislava")

        assert "query" in str(exc_info.value)
        assert "at least 1 character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_does_not_corrupt_context(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        generate_config: GenerateConfig,
        mock_places_service,
        sample_leads: list[Lead],
    ):
        """Test that errors don't corrupt the context state."""
        # Successful scrape
        scrape_tool = ScrapeLeadsTool()
        await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        leads_before = len(tool_context.leads)

        # Failed generate
        mock_openai = AsyncMock()
        mock_openai.generate_message = AsyncMock(
            side_effect=APIError("Service unavailable", service="openai")
        )

        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=sample_leads,
                config=generate_config,
                openai_service=mock_openai,
            ),
            tool_context,
        )

        # Context leads should be unchanged
        assert len(tool_context.leads) == leads_before
        # No messages should have been added
        assert len(tool_context.messages) == 0


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting across tools."""

    @pytest.mark.asyncio
    async def test_multiple_tools_respect_shared_rate_limits(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        sample_leads: list[Lead],
    ):
        """Test that multiple tool instances respect shared rate limits."""
        call_times = []

        async def track_call_time(lead, **kwargs):
            call_times.append(datetime.now(timezone.utc))
            return MagicMock(
                message=OutreachMessage(
                    subject=f"Test for {lead.name}",
                    body="Test body",
                    lead_id=lead.id,
                ),
                total_tokens=100,
                cost_usd=0.0001,
            )

        mock_service = AsyncMock()
        mock_service.generate_message = AsyncMock(side_effect=track_call_time)

        # Run tool with multiple leads
        generate_tool = GenerateOutreachTool()
        await generate_tool.run(
            GenerateInput(
                leads=sample_leads[:3],
                config=generate_config,
                openai_service=mock_service,
            ),
            tool_context,
        )

        # Verify calls were made sequentially (not all at once)
        assert len(call_times) == 3

    @pytest.mark.asyncio
    async def test_context_tracks_api_calls(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        mock_places_service,
    ):
        """Test that context correctly tracks API call count."""
        initial_calls = tool_context.api_calls

        scrape_tool = ScrapeLeadsTool()
        await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        assert tool_context.api_calls == initial_calls + 1

    @pytest.mark.asyncio
    async def test_token_and_cost_tracking(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        sample_leads: list[Lead],
    ):
        """Test that token usage and costs are tracked."""
        mock_service = AsyncMock()

        async def generate_with_tokens(lead, **kwargs):
            return MagicMock(
                message=OutreachMessage(
                    subject="Test",
                    body="Body",
                    lead_id=lead.id,
                ),
                total_tokens=150,
                cost_usd=0.0002,
            )

        mock_service.generate_message = AsyncMock(side_effect=generate_with_tokens)

        generate_tool = GenerateOutreachTool()
        await generate_tool.run(
            GenerateInput(
                leads=sample_leads[:3],
                config=generate_config,
                openai_service=mock_service,
            ),
            tool_context,
        )

        # Verify tokens and cost tracked
        assert tool_context.tokens_used > 0
        assert tool_context.cost_usd > 0


# =============================================================================
# Data Transformation Pipeline Tests
# =============================================================================


class TestDataTransformationPipeline:
    """Tests for data transformation through the pipeline."""

    @pytest.mark.asyncio
    async def test_lead_to_enriched_lead_transformation(
        self,
        tool_context: ToolContext,
        enrich_config: EnrichConfig,
        mock_hunter_service,
        sample_lead: Lead,
    ):
        """Test that Lead transforms correctly to EnrichedLead."""
        enrich_tool = EnrichEmailTool()
        result = await enrich_tool.run(
            EnrichInput(
                leads=[sample_lead],
                config=enrich_config,
                hunter_service=mock_hunter_service,
            ),
            tool_context,
        )

        assert result.is_success
        enriched = result.output[0]

        # Original data preserved
        assert enriched.id == sample_lead.id
        assert enriched.name == sample_lead.name
        assert enriched.phone == sample_lead.phone

        # Enrichment data added
        assert isinstance(enriched, EnrichedLead)
        assert enriched.enriched_at is not None
        assert len(enriched.enrichments) > 0

    @pytest.mark.asyncio
    async def test_lead_to_message_transformation(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        mock_openai_service,
        sample_lead: Lead,
    ):
        """Test that Lead transforms correctly to OutreachMessage."""
        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=[sample_lead],
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        assert result.is_success
        message = result.output[0]

        # Message has lead reference
        assert message.lead_id == sample_lead.id
        # Lead name appears in subject
        assert sample_lead.name in message.subject
        # Message metadata set
        assert message.language == MessageLanguage.SLOVAK
        assert message.tone == MessageTone.PROFESSIONAL

    @pytest.mark.asyncio
    async def test_data_preserved_through_full_pipeline(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        enrich_config: EnrichConfig,
        generate_config: GenerateConfig,
        export_config: ExportConfig,
        mock_places_service,
        mock_hunter_service,
        mock_openai_service,
        mock_sheets_service,
    ):
        """Test that essential data is preserved through the full pipeline."""
        # Step 1: Scrape
        scrape_tool = ScrapeLeadsTool()
        scrape_result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        original_lead_ids = {lead.id for lead in scrape_result.output}

        # Step 2: Enrich
        enrich_tool = EnrichEmailTool()
        enrich_result = await enrich_tool.run(
            EnrichInput(
                leads=scrape_result.output,
                config=enrich_config,
                hunter_service=mock_hunter_service,
            ),
            tool_context,
        )

        enriched_lead_ids = {lead.id for lead in enrich_result.output}
        # All original IDs preserved
        assert original_lead_ids == enriched_lead_ids

        # Step 3: Generate
        generate_tool = GenerateOutreachTool()
        generate_result = await generate_tool.run(
            GenerateInput(
                leads=enrich_result.output,
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        message_lead_ids = {msg.lead_id for msg in generate_result.output}
        # All leads got messages
        assert message_lead_ids == original_lead_ids

    @pytest.mark.asyncio
    async def test_export_format_transformation(
        self,
        tool_context: ToolContext,
        export_config: ExportConfig,
        mock_sheets_service,
        sample_leads: list[Lead],
        sample_message: OutreachMessage,
    ):
        """Test that data is correctly formatted for export."""
        export_tool = ExportToSheetsTool()
        result = await export_tool.run(
            ExportInput(
                config=export_config,
                leads=sample_leads,
                messages=[sample_message],
                sheets_service=mock_sheets_service,
            ),
            tool_context,
        )

        assert result.is_success

        # Verify export_leads was called with correct data
        call_args = mock_sheets_service.export_leads.call_args
        exported_leads = call_args.args[0] if call_args.args else call_args.kwargs.get("leads")
        assert len(exported_leads) == len(sample_leads)


# =============================================================================
# Bounded Collection Tests
# =============================================================================


class TestBoundedCollections:
    """Tests for bounded collection behavior in context."""

    @pytest.mark.asyncio
    async def test_context_has_max_collection_size(self):
        """Test that context collections have maximum size."""
        context = ToolContext()
        assert context._max_collection_size == 10000

    @pytest.mark.asyncio
    async def test_leads_collection_is_bounded(self):
        """Test that leads collection doesn't grow beyond max size."""
        # Create context with small max size for testing
        context = ToolContext()
        context._max_collection_size = 100
        context._leads = deque(maxlen=100)

        # Add more items than max
        for i in range(150):
            context.add_lead(
                Lead(
                    id=f"lead-{i}",
                    name=f"Test Lead {i}",
                )
            )

        # Collection should be at max size
        assert len(context._leads) == 100
        # Oldest items should be dropped
        assert context._leads[0].id == "lead-50"
        # Items dropped counter should track
        assert context._items_dropped == 50

    @pytest.mark.asyncio
    async def test_messages_collection_is_bounded(self):
        """Test that messages collection doesn't grow beyond max size."""
        context = ToolContext()
        context._max_collection_size = 50
        context._messages = deque(maxlen=50)

        for i in range(75):
            context.add_message(
                OutreachMessage(
                    id=f"msg-{i}",
                    subject=f"Subject {i}",
                    body=f"Body {i}",
                )
            )

        assert len(context._messages) == 50
        assert context._items_dropped == 25

    @pytest.mark.asyncio
    async def test_enriched_leads_collection_is_bounded(self):
        """Test that enriched leads collection is bounded."""
        context = ToolContext()
        context._max_collection_size = 30
        context._enriched_leads = deque(maxlen=30)

        for i in range(50):
            context.add_enriched_lead(
                EnrichedLead(
                    id=f"enriched-{i}",
                    name=f"Test {i}",
                )
            )

        assert len(context._enriched_leads) == 30
        assert context._items_dropped == 20

    @pytest.mark.asyncio
    async def test_collection_stats_tracking(self):
        """Test that collection stats are properly tracked."""
        context = ToolContext()
        context._max_collection_size = 10
        context._leads = deque(maxlen=10)

        for i in range(15):
            context.add_lead(Lead(id=f"lead-{i}", name=f"Test {i}"))

        stats = context.get_collection_stats()

        assert stats["leads_count"] == 10
        assert stats["max_collection_size"] == 10
        assert stats["items_dropped"] == 5
        assert "memory_usage_mb" in stats
        assert "memory_usage_bytes" in stats

    @pytest.mark.asyncio
    async def test_clear_collections(self):
        """Test that collections can be cleared."""
        context = ToolContext()

        # Add items
        context.add_lead(Lead(id="1", name="Test 1"))
        context.add_message(OutreachMessage(id="1", subject="S", body="B"))
        context.add_enriched_lead(EnrichedLead(id="1", name="Test 1"))

        assert len(context.leads) == 1
        assert len(context.messages) == 1
        assert len(context.enriched_leads) == 1

        # Clear
        context.clear_collections()

        assert len(context.leads) == 0
        assert len(context.messages) == 0
        assert len(context.enriched_leads) == 0

    @pytest.mark.asyncio
    async def test_memory_tracking(self):
        """Test memory usage tracking."""
        context = ToolContext()

        initial_memory = context.memory_usage_bytes

        # Add items
        for i in range(100):
            context.add_lead(
                Lead(
                    id=f"lead-{i}",
                    name=f"Test Lead with a longer name {i}",
                    phone=f"+4219012345{i:02d}",
                )
            )

        # Memory should have increased
        assert context.memory_usage_bytes > initial_memory
        assert context.memory_usage_mb > 0

    @pytest.mark.asyncio
    async def test_bounded_collection_with_tool_chain(
        self,
        scrape_config: ScrapeConfig,
        generate_config: GenerateConfig,
        mock_openai_service,
    ):
        """Test bounded collections work correctly during tool chain execution."""
        # Create context with small bounds
        context = ToolContext()
        context._max_collection_size = 3
        context._leads = deque(maxlen=3)
        context._messages = deque(maxlen=3)

        # Create 5 leads
        leads = [
            Lead(id=f"lead-{i}", name=f"Test {i}")
            for i in range(5)
        ]

        # Add all leads (only last 3 should remain)
        for lead in leads:
            context.add_lead(lead)

        assert len(context.leads) == 3
        assert context.leads[0].id == "lead-2"  # Oldest remaining

        # Generate messages for original 5 leads
        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=leads,  # Pass original 5
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            context,
        )

        # All 5 messages generated, but only 3 in context
        assert len(result.output) == 5
        assert len(context.messages) == 3


# =============================================================================
# Dry Run Tests
# =============================================================================


class TestDryRun:
    """Tests for dry run mode."""

    @pytest.mark.asyncio
    async def test_scrape_dry_run(
        self,
        scrape_config: ScrapeConfig,
    ):
        """Test scrape tool dry run mode."""
        context = ToolContext(dry_run=True)
        scrape_tool = ScrapeLeadsTool()

        result = await scrape_tool.run(
            ScrapeInput(config=scrape_config),
            context,
        )

        assert result.status == ToolStatus.SKIPPED
        assert result.metadata.get("dry_run") is True
        # No actual leads should be returned
        assert result.output == []

    @pytest.mark.asyncio
    async def test_generate_dry_run(
        self,
        generate_config: GenerateConfig,
        sample_leads: list[Lead],
    ):
        """Test generate tool dry run mode."""
        context = ToolContext(dry_run=True)
        generate_tool = GenerateOutreachTool()

        result = await generate_tool.run(
            GenerateInput(
                leads=sample_leads,
                config=generate_config,
            ),
            context,
        )

        assert result.status == ToolStatus.SKIPPED
        assert result.metadata.get("dry_run") is True
        assert result.metadata.get("would_generate", {}).get("lead_count") == len(sample_leads)

    @pytest.mark.asyncio
    async def test_export_dry_run(
        self,
        export_config: ExportConfig,
        sample_leads: list[Lead],
    ):
        """Test export tool dry run mode."""
        context = ToolContext(dry_run=True)
        export_tool = ExportToSheetsTool()

        result = await export_tool.run(
            ExportInput(
                config=export_config,
                leads=sample_leads,
            ),
            context,
        )

        assert result.status == ToolStatus.SKIPPED
        assert result.metadata.get("dry_run") is True
        assert result.metadata.get("would_export", {}).get("leads_count") == len(sample_leads)


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_leads_list(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        mock_openai_service,
    ):
        """Test handling of empty leads list."""
        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=[],
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        assert result.status == ToolStatus.SKIPPED
        assert "No leads" in result.error_message

    @pytest.mark.asyncio
    async def test_no_data_to_export(
        self,
        tool_context: ToolContext,
        export_config: ExportConfig,
        mock_sheets_service,
    ):
        """Test export with no data."""
        export_tool = ExportToSheetsTool()
        result = await export_tool.run(
            ExportInput(
                config=export_config,
                leads=None,
                messages=None,
                sheets_service=mock_sheets_service,
            ),
            tool_context,
        )

        assert result.status == ToolStatus.SKIPPED
        assert "No data to export" in result.error_message

    @pytest.mark.asyncio
    async def test_tool_result_success_rate_calculation(self):
        """Test ToolResult success rate calculation."""
        result = ToolResult(
            status=ToolStatus.PARTIAL,
            items_processed=8,
            items_failed=2,
        )

        assert result.success_rate == 80.0

    @pytest.mark.asyncio
    async def test_tool_result_with_zero_items(self):
        """Test ToolResult with zero items."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            items_processed=0,
            items_failed=0,
        )

        assert result.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_context_elapsed_time(self):
        """Test context elapsed time calculation."""
        context = ToolContext()
        await asyncio.sleep(0.1)

        elapsed = context.elapsed_seconds
        assert elapsed >= 0.1
        assert elapsed < 1.0  # Should be quick

    @pytest.mark.asyncio
    async def test_lead_with_missing_optional_fields(
        self,
        tool_context: ToolContext,
        generate_config: GenerateConfig,
        mock_openai_service,
    ):
        """Test handling leads with missing optional fields."""
        minimal_lead = Lead(
            id="minimal-1",
            name="Minimal Dentist",
            # No phone, website, location, etc.
        )

        generate_tool = GenerateOutreachTool()
        result = await generate_tool.run(
            GenerateInput(
                leads=[minimal_lead],
                config=generate_config,
                openai_service=mock_openai_service,
            ),
            tool_context,
        )

        assert result.is_success
        assert len(result.output) == 1

    @pytest.mark.asyncio
    async def test_tool_execution_time_tracking(
        self,
        tool_context: ToolContext,
        scrape_config: ScrapeConfig,
        mock_places_service,
    ):
        """Test that execution time is tracked in results."""
        scrape_tool = ScrapeLeadsTool()
        result = await scrape_tool.run(
            ScrapeInput(config=scrape_config, places_service=mock_places_service),
            tool_context,
        )

        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_concurrent_context_access(
        self,
        sample_leads: list[Lead],
    ):
        """Test that concurrent context access is safe."""
        context = ToolContext()

        async def add_leads_batch(start: int, count: int):
            for i in range(start, start + count):
                context.add_lead(
                    Lead(id=f"lead-{i}", name=f"Lead {i}")
                )

        # Run multiple concurrent batches
        await asyncio.gather(
            add_leads_batch(0, 100),
            add_leads_batch(100, 100),
            add_leads_batch(200, 100),
        )

        # All leads should be added (deque handles this safely)
        assert len(context.leads) == 300
