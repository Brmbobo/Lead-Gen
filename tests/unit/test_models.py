"""
Unit tests for domain models.
"""

import pytest
from datetime import datetime, timezone

from lead_gen.models.lead import (
    Lead,
    EnrichedLead,
    EmailEnrichment,
    Location,
    BusinessMetrics,
    LeadSource,
    LeadStatus,
)
from lead_gen.models.outreach import (
    OutreachMessage,
    MessageTemplate,
    PersonalizationContext,
    MessageLanguage,
    MessageTone,
)
from lead_gen.models.workflow import (
    WorkflowConfig,
    WorkflowStep,
    StepType,
    ScrapeConfig,
)


class TestLeadModel:
    """Tests for Lead model."""

    def test_lead_creation(self, sample_lead: Lead) -> None:
        """Test basic lead creation."""
        assert sample_lead.name == "Zubná Ambulancia Dr. Novák"
        assert sample_lead.phone == "+421901234567"
        assert sample_lead.status == LeadStatus.NEW

    def test_lead_quality_score(self, sample_lead: Lead) -> None:
        """Test quality score calculation."""
        score = sample_lead.quality_score
        assert 0 <= score <= 100
        assert score > 50  # Should have decent score with all fields

    def test_lead_has_contact_info(self, sample_lead: Lead) -> None:
        """Test contact info detection."""
        assert sample_lead.has_contact_info is True

        empty_lead = Lead(name="Test", phone="")
        assert empty_lead.has_contact_info is False

    def test_lead_export_dict(self, sample_lead: Lead) -> None:
        """Test export to dictionary."""
        export = sample_lead.to_export_dict()

        assert "id" in export
        assert "name" in export
        assert export["name"] == sample_lead.name
        assert "quality_score" in export

    def test_lead_gdpr_export(self, sample_lead: Lead) -> None:
        """Test GDPR export."""
        export = sample_lead.to_gdpr_export()

        assert "personal_data" in export
        assert "processing_metadata" in export
        assert export["personal_data"]["business_name"] == sample_lead.name


class TestEnrichedLeadModel:
    """Tests for EnrichedLead model."""

    def test_enriched_lead_creation(self, sample_lead: Lead) -> None:
        """Test enriched lead creation."""
        enrichment = EmailEnrichment(
            email="test@example.sk",
            confidence=85,
            first_name="Test",
            last_name="User",
        )

        enriched = EnrichedLead(
            **sample_lead.model_dump(),
            enrichments=[enrichment],
            enriched_at=datetime.now(timezone.utc),
        )

        assert enriched.best_email == "test@example.sk"
        assert enriched.contact_person == "Test User"
        assert enriched.enrichment_quality == "medium"

    def test_enriched_lead_best_email(self, sample_lead: Lead) -> None:
        """Test best email selection."""
        enrichments = [
            EmailEnrichment(email="low@example.sk", confidence=30),
            EmailEnrichment(email="high@example.sk", confidence=90),
            EmailEnrichment(email="mid@example.sk", confidence=60),
        ]

        enriched = EnrichedLead(
            **sample_lead.model_dump(),
            enrichments=enrichments,
        )

        # Should return highest confidence email
        assert enriched.best_email == "high@example.sk"


class TestOutreachMessageModel:
    """Tests for OutreachMessage model."""

    def test_message_creation(self, sample_message: OutreachMessage) -> None:
        """Test message creation."""
        assert sample_message.subject.startswith("Spolupráca")
        assert sample_message.language == MessageLanguage.SLOVAK

    def test_message_word_count(self, sample_message: OutreachMessage) -> None:
        """Test word count calculation."""
        assert sample_message.word_count > 0
        assert sample_message.character_count > 0

    def test_message_engagement_score(self, sample_message: OutreachMessage) -> None:
        """Test engagement score calculation."""
        # Unsent message should have 0 engagement
        assert sample_message.engagement_score == 0

        # Mark as sent
        sample_message.mark_sent("test@example.sk")
        assert sample_message.engagement_score == 10

        # Mark as opened
        sample_message.mark_opened()
        assert sample_message.engagement_score == 40


class TestMessageTemplate:
    """Tests for MessageTemplate model."""

    def test_template_creation(self) -> None:
        """Test template creation."""
        template = MessageTemplate(
            name="Test Template",
            subject="Hello {business_name}",
            body="Dear {contact_name},\n\nThis is a test.",
        )

        assert template.name == "Test Template"
        assert "{business_name}" in template.subject

    def test_template_render(self) -> None:
        """Test template rendering."""
        template = MessageTemplate(
            name="Test Template",
            subject="Hello {business_name}",
            body="Dear team at {business_name} in {city}.",
        )

        context = PersonalizationContext(
            business_name="Test Company",
            city="Bratislava",
        )

        subject, body = template.render(context)

        assert subject == "Hello Test Company"
        assert "Test Company" in body
        assert "Bratislava" in body


class TestWorkflowConfig:
    """Tests for WorkflowConfig model."""

    def test_workflow_creation(self) -> None:
        """Test workflow creation."""
        config = WorkflowConfig(
            name="test_workflow",
            description="Test workflow",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                )
            ],
        )

        assert config.name == "test_workflow"
        assert len(config.steps) == 1

    def test_workflow_validation(self) -> None:
        """Test workflow validation."""
        # Valid workflow
        config = WorkflowConfig(
            name="valid_workflow",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                )
            ],
        )

        errors = config.validate_workflow()
        assert len(errors) == 0

    def test_workflow_from_yaml_string(self) -> None:
        """Test loading workflow from YAML string."""
        yaml_str = """
name: test
steps:
  - name: scrape
    type: scrape
    scrape_config:
      query: test
"""
        config = WorkflowConfig.from_yaml_string(yaml_str)

        assert config.name == "test"
        assert len(config.steps) == 1
