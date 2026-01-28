"""
Domain models for Lead-Gen.

Provides Pydantic v2 models for:
- Lead: Business lead with contact information
- EnrichedLead: Lead with additional email data
- OutreachMessage: AI-generated personalized message
- WorkflowConfig: YAML workflow configuration
"""

from lead_gen.models.lead import (
    Lead,
    EnrichedLead,
    LeadSource,
    LeadStatus,
    GDPRConsent,
)
from lead_gen.models.outreach import (
    OutreachMessage,
    MessageTemplate,
    PersonalizationContext,
)
from lead_gen.models.workflow import (
    WorkflowConfig,
    WorkflowStep,
    StepType,
    WorkflowStatus,
)

__all__ = [
    # Lead models
    "Lead",
    "EnrichedLead",
    "LeadSource",
    "LeadStatus",
    "GDPRConsent",
    # Outreach models
    "OutreachMessage",
    "MessageTemplate",
    "PersonalizationContext",
    # Workflow models
    "WorkflowConfig",
    "WorkflowStep",
    "StepType",
    "WorkflowStatus",
]
