"""
Input sanitization and validation for security.

Provides protection against:
- Prompt injection attacks (LLM safety)
- SQL injection (if database used)
- XSS (if web interface used)
- Path traversal
- Command injection
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import structlog

from lead_gen.core.exceptions import SecurityError, ValidationError

logger = structlog.get_logger(__name__)


class ThreatType(str, Enum):
    """Types of detected security threats."""

    PROMPT_INJECTION = "prompt_injection"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    SSRF = "ssrf"


@dataclass
class SanitizationResult:
    """Result of sanitization operation."""

    original: str
    sanitized: str
    threats_detected: list[ThreatType]
    was_modified: bool

    @property
    def is_safe(self) -> bool:
        """Check if no threats were detected."""
        return len(self.threats_detected) == 0


# Common prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction override
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|above)",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?:",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    # Role manipulation
    r"you\s+are\s+now",
    r"act\s+as\s+(a|an|if)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"roleplay\s+as",
    # Output manipulation
    r"print\s+(the\s+)?(previous|above|system)",
    r"reveal\s+(the\s+)?(system|hidden|secret)",
    r"show\s+(me\s+)?(the\s+)?(prompt|instructions)",
    # Delimiter injection
    r"```(system|assistant|user)",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"('|\")\s*(or|and)\s*('|\")?1('|\")?=('|\")?1",
    r";\s*(drop|delete|truncate|update|insert)\s",
    r"union\s+(all\s+)?select",
    r"--\s*$",
    r"/\*.*\*/",
    r"exec\s*\(",
    r"execute\s*\(",
    r"xp_\w+",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"<svg[^>]*onload",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"\.%2e/",
    r"%2e\./",
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r";\s*\w+",
    r"\|\s*\w+",
    r"`[^`]+`",
    r"\$\([^)]+\)",
    r"&&\s*\w+",
    r"\|\|\s*\w+",
]


def detect_prompt_injection(text: str) -> list[str]:
    """
    Detect potential prompt injection attacks.

    Args:
        text: Input text to check

    Returns:
        List of detected patterns
    """
    detected = []
    text_lower = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            detected.append(pattern)

    return detected


def detect_sql_injection(text: str) -> list[str]:
    """
    Detect potential SQL injection attacks.

    Args:
        text: Input text to check

    Returns:
        List of detected patterns
    """
    detected = []
    text_lower = text.lower()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            detected.append(pattern)

    return detected


def detect_xss(text: str) -> list[str]:
    """
    Detect potential XSS attacks.

    Args:
        text: Input text to check

    Returns:
        List of detected patterns
    """
    detected = []
    text_lower = text.lower()

    for pattern in XSS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            detected.append(pattern)

    return detected


def detect_path_traversal(text: str) -> list[str]:
    """
    Detect potential path traversal attacks.

    Args:
        text: Input text to check

    Returns:
        List of detected patterns
    """
    detected = []

    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected.append(pattern)

    return detected


def detect_command_injection(text: str) -> list[str]:
    """
    Detect potential command injection attacks.

    Args:
        text: Input text to check

    Returns:
        List of detected patterns
    """
    detected = []

    for pattern in COMMAND_INJECTION_PATTERNS:
        if re.search(pattern, text):
            detected.append(pattern)

    return detected


def sanitize_for_llm(text: str, strict: bool = True) -> SanitizationResult:
    """
    Sanitize text for use in LLM prompts.

    Removes or escapes potential prompt injection attacks.

    Args:
        text: Input text to sanitize
        strict: If True, raise exception on detected threats

    Returns:
        SanitizationResult with sanitized text

    Raises:
        SecurityError: If strict=True and threats detected
    """
    threats: list[ThreatType] = []
    sanitized = text

    # Check for prompt injection
    injection_patterns = detect_prompt_injection(text)
    if injection_patterns:
        threats.append(ThreatType.PROMPT_INJECTION)
        logger.warning(
            "prompt_injection_detected",
            patterns=injection_patterns[:3],  # Limit logged patterns
            input_length=len(text),
        )

        if strict:
            raise SecurityError(
                "Potential prompt injection detected in input",
                threat_type=ThreatType.PROMPT_INJECTION.value,
            )

        # Remove dangerous patterns
        for pattern in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)

    # Escape special LLM delimiters
    escape_sequences = [
        ("```", "` ` `"),
        ("<<<", "< < <"),
        (">>>", "> > >"),
        ("[[", "[ ["),
        ("]]", "] ]"),
    ]

    for old, new in escape_sequences:
        if old in sanitized:
            sanitized = sanitized.replace(old, new)

    return SanitizationResult(
        original=text,
        sanitized=sanitized,
        threats_detected=threats,
        was_modified=text != sanitized,
    )


def sanitize_for_html(text: str) -> SanitizationResult:
    """
    Sanitize text for HTML output.

    Escapes HTML entities and removes XSS vectors.

    Args:
        text: Input text to sanitize

    Returns:
        SanitizationResult with sanitized text
    """
    threats: list[ThreatType] = []

    # Check for XSS
    xss_patterns = detect_xss(text)
    if xss_patterns:
        threats.append(ThreatType.XSS)
        logger.warning(
            "xss_detected",
            patterns=xss_patterns[:3],
        )

    # HTML escape
    sanitized = html.escape(text, quote=True)

    return SanitizationResult(
        original=text,
        sanitized=sanitized,
        threats_detected=threats,
        was_modified=text != sanitized,
    )


def validate_url(url: str, allowed_schemes: list[str] | None = None) -> str:
    """
    Validate and sanitize a URL.

    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: https only)

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid or uses disallowed scheme
    """
    if allowed_schemes is None:
        allowed_schemes = ["https"]

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"Invalid URL format: {e}",
            field_name="url",
            field_value=url,
        )

    # Check scheme
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(
            f"URL scheme '{parsed.scheme}' not allowed. Allowed: {allowed_schemes}",
            field_name="url",
            field_value=url,
            constraint=f"scheme in {allowed_schemes}",
        )

    # Check for SSRF indicators
    hostname = parsed.hostname or ""
    suspicious_hosts = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    ]

    if hostname.lower() in suspicious_hosts:
        raise SecurityError(
            f"URL points to potentially dangerous host: {hostname}",
            threat_type=ThreatType.SSRF.value,
        )

    # Check for path traversal in URL path
    if parsed.path:
        traversal = detect_path_traversal(parsed.path)
        if traversal:
            raise SecurityError(
                "Path traversal detected in URL",
                threat_type=ThreatType.PATH_TRAVERSAL.value,
            )

    return url


def validate_email(email: str) -> str:
    """
    Validate an email address format.

    Args:
        email: Email address to validate

    Returns:
        Validated email (lowercased)

    Raises:
        ValidationError: If email format is invalid
    """
    # Basic email regex (not perfect but catches most issues)
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, email):
        raise ValidationError(
            "Invalid email format",
            field_name="email",
            constraint="valid email format",
        )

    # Additional checks
    if ".." in email:
        raise ValidationError(
            "Invalid email: consecutive dots not allowed",
            field_name="email",
        )

    return email.lower()


def validate_phone(phone: str, country_code: str = "SK") -> str:
    """
    Validate and normalize a phone number.

    Args:
        phone: Phone number to validate
        country_code: ISO country code for validation

    Returns:
        Normalized phone number

    Raises:
        ValidationError: If phone format is invalid
    """
    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)

    # Slovak/Czech phone patterns
    patterns = {
        "SK": r"^(\+421|00421|0)?[0-9]{9}$",
        "CZ": r"^(\+420|00420|0)?[0-9]{9}$",
        "AT": r"^(\+43|0043|0)?[0-9]{10,13}$",
    }

    pattern = patterns.get(country_code, r"^\+?[0-9]{8,15}$")

    if not re.match(pattern, cleaned):
        raise ValidationError(
            f"Invalid phone number format for country {country_code}",
            field_name="phone",
            constraint=f"valid {country_code} phone format",
        )

    # Normalize to international format
    if country_code == "SK" and cleaned.startswith("0"):
        cleaned = "+421" + cleaned[1:]
    elif country_code == "CZ" and cleaned.startswith("0"):
        cleaned = "+420" + cleaned[1:]
    elif country_code == "AT" and cleaned.startswith("0"):
        cleaned = "+43" + cleaned[1:]

    return cleaned


def sanitize_business_name(name: str) -> str:
    """
    Sanitize a business name for safe storage and display.

    Args:
        name: Business name to sanitize

    Returns:
        Sanitized business name
    """
    # Remove control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", name)

    # Normalize whitespace
    sanitized = " ".join(sanitized.split())

    # Limit length
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit(" ", 1)[0] + "..."

    return sanitized


class InputSanitizer:
    """
    Unified input sanitizer for all input types.

    Example:
        >>> sanitizer = InputSanitizer()
        >>> result = sanitizer.sanitize(user_input, context="llm_prompt")
    """

    def __init__(self, strict: bool = True) -> None:
        """
        Initialize sanitizer.

        Args:
            strict: If True, raise exceptions on detected threats
        """
        self.strict = strict
        self._threat_count: dict[ThreatType, int] = {t: 0 for t in ThreatType}

    def sanitize(
        self,
        value: str,
        context: str = "general",
        field_name: str | None = None,
    ) -> SanitizationResult:
        """
        Sanitize input based on context.

        Args:
            value: Input value to sanitize
            context: Context for sanitization (llm_prompt, html, url, email, phone, business_name)
            field_name: Optional field name for error messages

        Returns:
            SanitizationResult

        Raises:
            SecurityError: If strict mode and threats detected
            ValidationError: If input is invalid for context
        """
        if context == "llm_prompt":
            return sanitize_for_llm(value, strict=self.strict)
        elif context == "html":
            return sanitize_for_html(value)
        elif context == "url":
            validated = validate_url(value)
            return SanitizationResult(
                original=value,
                sanitized=validated,
                threats_detected=[],
                was_modified=False,
            )
        elif context == "email":
            validated = validate_email(value)
            return SanitizationResult(
                original=value,
                sanitized=validated,
                threats_detected=[],
                was_modified=value != validated,
            )
        elif context == "phone":
            validated = validate_phone(value)
            return SanitizationResult(
                original=value,
                sanitized=validated,
                threats_detected=[],
                was_modified=value != validated,
            )
        elif context == "business_name":
            sanitized = sanitize_business_name(value)
            return SanitizationResult(
                original=value,
                sanitized=sanitized,
                threats_detected=[],
                was_modified=value != sanitized,
            )
        else:
            # General sanitization - check all threats
            threats: list[ThreatType] = []
            sanitized = value

            if detect_prompt_injection(value):
                threats.append(ThreatType.PROMPT_INJECTION)
            if detect_sql_injection(value):
                threats.append(ThreatType.SQL_INJECTION)
            if detect_xss(value):
                threats.append(ThreatType.XSS)

            if threats:
                for t in threats:
                    self._threat_count[t] += 1

                if self.strict:
                    raise SecurityError(
                        f"Security threats detected: {[t.value for t in threats]}",
                        threat_type=threats[0].value,
                    )

                # Basic sanitization
                sanitized = html.escape(value)

            return SanitizationResult(
                original=value,
                sanitized=sanitized,
                threats_detected=threats,
                was_modified=value != sanitized,
            )

    def get_threat_statistics(self) -> dict[str, int]:
        """Get count of detected threats by type."""
        return {t.value: count for t, count in self._threat_count.items()}
