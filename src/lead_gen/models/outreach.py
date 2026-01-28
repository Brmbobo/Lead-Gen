"""
Outreach message models for AI-generated content.

Provides models for:
- Message templates with variables
- Personalization context
- Generated outreach messages
- A/B testing variants
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class MessageLanguage(str, Enum):
    """Supported message languages."""

    SLOVAK = "sk"
    CZECH = "cs"
    GERMAN = "de"
    ENGLISH = "en"


class MessageTone(str, Enum):
    """Message tone/style."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"
    ENTHUSIASTIC = "enthusiastic"


class MessageType(str, Enum):
    """Type of outreach message."""

    COLD_EMAIL = "cold_email"
    FOLLOW_UP = "follow_up"
    INTRODUCTION = "introduction"
    PARTNERSHIP = "partnership"
    FEEDBACK_REQUEST = "feedback_request"


class PersonalizationContext(BaseModel):
    """
    Context for message personalization.

    Contains all variables that can be used in templates.
    """

    model_config = ConfigDict(frozen=True)

    # Business info
    business_name: str
    business_type: str = ""
    city: str = ""
    region: str = ""
    country: str = ""

    # Contact info (if available)
    contact_name: str = ""
    contact_position: str = ""

    # Metrics
    rating: float | None = None
    review_count: int = 0

    # Custom variables
    custom_vars: dict[str, str] = Field(default_factory=dict)

    # Sender info
    sender_name: str = ""
    sender_company: str = ""
    sender_position: str = ""
    sender_email: str = ""
    sender_phone: str = ""

    # Campaign info
    campaign_name: str = ""
    value_proposition: str = ""

    def get_variable(self, name: str, default: str = "") -> str:
        """Get a variable value by name."""
        # Check custom vars first
        if name in self.custom_vars:
            return self.custom_vars[name]

        # Then check model fields
        if hasattr(self, name):
            value = getattr(self, name)
            if value is not None:
                return str(value)

        return default

    def to_template_vars(self) -> dict[str, str]:
        """Convert to dictionary for template rendering."""
        vars_dict = {
            "business_name": self.business_name,
            "business_type": self.business_type,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "contact_name": self.contact_name,
            "contact_position": self.contact_position,
            "rating": str(self.rating) if self.rating else "",
            "review_count": str(self.review_count),
            "sender_name": self.sender_name,
            "sender_company": self.sender_company,
            "sender_position": self.sender_position,
            "sender_email": self.sender_email,
            "sender_phone": self.sender_phone,
            "campaign_name": self.campaign_name,
            "value_proposition": self.value_proposition,
        }
        vars_dict.update(self.custom_vars)
        return vars_dict


class MessageTemplate(BaseModel):
    """
    Message template with variables.

    Templates use {variable_name} syntax for interpolation.

    Example:
        >>> template = MessageTemplate(
        ...     subject="Spolupráca pre {business_name}",
        ...     body="Dobrý deň,\\n\\nOsluvujem Vás z {sender_company}...",
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)

    # Content
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=10000)
    signature: str = ""

    # Metadata
    language: MessageLanguage = MessageLanguage.SLOVAK
    tone: MessageTone = MessageTone.PROFESSIONAL
    message_type: MessageType = MessageType.COLD_EMAIL

    # Variables
    required_variables: list[str] = Field(default_factory=list)
    optional_variables: list[str] = Field(default_factory=list)

    # A/B testing
    variant_name: str = ""  # For A/B testing
    is_control: bool = False

    # Performance tracking
    times_used: int = 0
    open_rate: float | None = None
    reply_rate: float | None = None

    @field_validator("body", mode="after")
    @classmethod
    def extract_variables(cls, v: str, info: Any) -> str:
        """Extract variables from template."""
        import re

        # Find all {variable} patterns
        variables = re.findall(r"\{(\w+)\}", v)

        # Store in info.data for later validation
        # This is a simplified approach
        return v

    def render(self, context: PersonalizationContext) -> tuple[str, str]:
        """
        Render template with context.

        Args:
            context: Personalization context with variable values

        Returns:
            Tuple of (rendered_subject, rendered_body)
        """
        import re

        vars_dict = context.to_template_vars()

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            return vars_dict.get(var_name, match.group(0))

        pattern = r"\{(\w+)\}"
        rendered_subject = re.sub(pattern, replace_var, self.subject)
        rendered_body = re.sub(pattern, replace_var, self.body)

        if self.signature:
            rendered_signature = re.sub(pattern, replace_var, self.signature)
            rendered_body = f"{rendered_body}\n\n{rendered_signature}"

        return rendered_subject, rendered_body

    def validate_context(self, context: PersonalizationContext) -> list[str]:
        """
        Validate that context has all required variables.

        Returns:
            List of missing required variables
        """
        import re

        # Find all variables in template
        all_vars = set(re.findall(r"\{(\w+)\}", self.subject + self.body))
        vars_dict = context.to_template_vars()

        missing = []
        for var in all_vars:
            if var in self.required_variables and not vars_dict.get(var):
                missing.append(var)

        return missing


class OutreachMessage(BaseModel):
    """
    Generated outreach message.

    Represents a personalized message ready to be sent.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Content
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=10000)
    html_body: str | None = None  # HTML version if needed

    # Metadata
    language: MessageLanguage = MessageLanguage.SLOVAK
    tone: MessageTone = MessageTone.PROFESSIONAL
    message_type: MessageType = MessageType.COLD_EMAIL

    # Generation info
    template_id: str | None = None
    lead_id: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generation_model: str = "gpt-4o-mini"
    generation_tokens: int = 0
    generation_cost_usd: float = 0.0

    # Personalization
    personalization_context: PersonalizationContext | None = None
    personalization_score: int = Field(default=0, ge=0, le=100)

    # Quality metrics
    readability_score: float | None = None  # Flesch-Kincaid or similar
    sentiment_score: float | None = None  # -1 to 1
    spam_score: float | None = None  # 0 to 1

    # Sending status
    sent_at: datetime | None = None
    sent_to: str = ""  # Email address
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    replied_at: datetime | None = None
    bounced: bool = False
    unsubscribed: bool = False

    # Correlation
    correlation_id: str | None = None
    campaign_id: str = ""
    sequence_number: int = 1  # For multi-touch campaigns

    @computed_field
    @property
    def word_count(self) -> int:
        """Count words in body."""
        return len(self.body.split())

    @computed_field
    @property
    def character_count(self) -> int:
        """Count characters in body."""
        return len(self.body)

    @computed_field
    @property
    def is_sent(self) -> bool:
        """Check if message was sent."""
        return self.sent_at is not None

    @computed_field
    @property
    def is_opened(self) -> bool:
        """Check if message was opened."""
        return self.opened_at is not None

    @computed_field
    @property
    def is_replied(self) -> bool:
        """Check if message received a reply."""
        return self.replied_at is not None

    @computed_field
    @property
    def engagement_score(self) -> int:
        """Calculate engagement score."""
        score = 0
        if self.is_sent:
            score += 10
        if self.is_opened:
            score += 30
        if self.clicked_at:
            score += 30
        if self.is_replied:
            score += 30
        if self.bounced:
            score -= 20
        if self.unsubscribed:
            score -= 10
        return max(0, min(100, score))

    def mark_sent(self, email: str) -> None:
        """Mark message as sent."""
        self.sent_at = datetime.now(timezone.utc)
        self.sent_to = email

    def mark_opened(self) -> None:
        """Mark message as opened."""
        if not self.opened_at:
            self.opened_at = datetime.now(timezone.utc)

    def mark_clicked(self) -> None:
        """Mark message link as clicked."""
        if not self.clicked_at:
            self.clicked_at = datetime.now(timezone.utc)
        self.mark_opened()

    def mark_replied(self) -> None:
        """Mark message as replied."""
        if not self.replied_at:
            self.replied_at = datetime.now(timezone.utc)
        self.mark_opened()

    def to_export_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "id": self.id,
            "subject": self.subject,
            "body_preview": self.body[:200] + "..." if len(self.body) > 200 else self.body,
            "lead_id": self.lead_id,
            "sent_to": self.sent_to,
            "sent_at": self.sent_at.isoformat() if self.sent_at else "",
            "opened": self.is_opened,
            "replied": self.is_replied,
            "engagement_score": self.engagement_score,
            "word_count": self.word_count,
            "language": self.language.value,
            "tone": self.tone.value,
        }


# Slovak language templates
SLOVAK_TEMPLATES = {
    "dentist_intro": MessageTemplate(
        id="sk-dentist-intro-v1",
        name="Zubná ambulancia - Úvod",
        subject="Spolupráca pre {business_name} - moderné riešenia",
        body="""Dobrý deň,

oslovujem Vás s ponukou, ktorá by mohla zaujímať {business_name}.

{value_proposition}

Boli by ste ochotní venovať mi 15 minút na krátky rozhovor o tom, ako by sme mohli spolupracovať?

S pozdravom,
{sender_name}
{sender_company}
{sender_phone}""",
        language=MessageLanguage.SLOVAK,
        tone=MessageTone.PROFESSIONAL,
        message_type=MessageType.COLD_EMAIL,
        required_variables=["business_name", "value_proposition", "sender_name"],
        optional_variables=["sender_company", "sender_phone"],
    ),
    "dentist_follow_up": MessageTemplate(
        id="sk-dentist-follow-v1",
        name="Zubná ambulancia - Follow-up",
        subject="Re: Spolupráca pre {business_name}",
        body="""Dobrý deň,

nadväzujem na svoj predchádzajúci email ohľadom spolupráce.

Chápem, že máte plný diár, ale verím, že naša ponuka by mohla {business_name} priniesť reálnu hodnotu.

Môžem Vám zavolať na krátky 5-minútový rozhovor?

S pozdravom,
{sender_name}""",
        language=MessageLanguage.SLOVAK,
        tone=MessageTone.FRIENDLY,
        message_type=MessageType.FOLLOW_UP,
        required_variables=["business_name", "sender_name"],
    ),
}
