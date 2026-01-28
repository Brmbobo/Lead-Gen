"""
Configuration management using Pydantic Settings.

Provides type-safe, validated configuration with support for:
- Environment variables
- .env files
- Nested configuration models
- Secret masking in logs
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log level configuration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecretBackend(str, Enum):
    """Secret management backend."""

    ENV = "env"
    VAULT = "vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"


class RateLimitSettings(BaseModel):
    """Rate limiting configuration per service."""

    google_places: int = Field(default=60, ge=1, le=1000, description="Requests per minute")
    openai: int = Field(default=60, ge=1, le=1000, description="Requests per minute")
    hunter: int = Field(default=30, ge=1, le=1000, description="Requests per minute")
    sheets: int = Field(default=60, ge=1, le=1000, description="Requests per minute")


class GDPRSettings(BaseModel):
    """GDPR compliance configuration."""

    retention_days: int = Field(default=90, ge=1, le=365, description="Data retention period")
    legal_basis: Literal["legitimate_interest", "consent"] = Field(
        default="legitimate_interest",
        description="Legal basis for data processing",
    )
    dpo_email: str = Field(default="dpo@company.com", description="Data Protection Officer email")
    enable_audit_log: bool = Field(default=True, description="Enable GDPR audit logging")


class VaultSettings(BaseModel):
    """HashiCorp Vault configuration."""

    addr: str = Field(default="", description="Vault server address")
    token: SecretStr = Field(default=SecretStr(""), description="Vault authentication token")
    mount_point: str = Field(default="secret", description="Vault mount point")
    secret_path: str = Field(default="lead-gen/api-keys", description="Path to secrets")


class AWSSettings(BaseModel):
    """AWS Secrets Manager configuration."""

    region: str = Field(default="eu-central-1", description="AWS region")
    secret_name: str = Field(default="lead-gen/api-keys", description="Secret name in AWS")


class OpenAISettings(BaseModel):
    """OpenAI API configuration."""

    model: str = Field(default="gpt-4o-mini", description="Model to use")
    max_tokens: int = Field(default=500, ge=1, le=4096, description="Max tokens for generation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")


class GoogleSheetsSettings(BaseModel):
    """Google Sheets configuration."""

    spreadsheet_id: str = Field(default="", description="Target spreadsheet ID")
    worksheet_name: str = Field(default="Leads", description="Target worksheet name")


class Settings(BaseSettings):
    """
    Main application settings.

    Configuration is loaded from environment variables and .env files.
    Secrets are masked when logged or serialized.

    Example:
        >>> settings = get_settings()
        >>> print(settings.environment)
        Environment.DEVELOPMENT
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_json: bool = Field(default=False, description="Enable JSON structured logging")

    # API Keys (secrets)
    google_places_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google Places API key",
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="OpenAI API key",
    )
    hunter_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Hunter.io API key (optional)",
    )

    # Google Service Account
    google_service_account_path: Path | None = Field(
        default=None,
        description="Path to service account JSON",
    )
    google_service_account_base64: SecretStr = Field(
        default=SecretStr(""),
        description="Base64 encoded service account JSON",
    )

    # Secret Backend
    secret_backend: SecretBackend = Field(
        default=SecretBackend.ENV,
        description="Secret management backend",
    )

    # Nested Settings
    rate_limits: RateLimitSettings = Field(default_factory=RateLimitSettings)
    gdpr: GDPRSettings = Field(default_factory=GDPRSettings)
    vault: VaultSettings = Field(default_factory=VaultSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    sheets: GoogleSheetsSettings = Field(default_factory=GoogleSheetsSettings)

    @field_validator("google_service_account_path", mode="before")
    @classmethod
    def validate_service_account_path(cls, v: str | Path | None) -> Path | None:
        """Validate service account path exists if provided."""
        if v is None or v == "":
            return None
        path = Path(v) if isinstance(v, str) else v
        if not path.exists():
            # Don't fail, might use base64 instead
            return None
        return path

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def get_google_places_key(self) -> str:
        """Get Google Places API key (resolved from secret backend if needed)."""
        return self.google_places_api_key.get_secret_value()

    def get_openai_key(self) -> str:
        """Get OpenAI API key (resolved from secret backend if needed)."""
        return self.openai_api_key.get_secret_value()

    def get_hunter_key(self) -> str:
        """Get Hunter.io API key (resolved from secret backend if needed)."""
        return self.hunter_api_key.get_secret_value()

    def validate_required_keys(self, require_hunter: bool = False) -> list[str]:
        """
        Validate that required API keys are configured.

        Args:
            require_hunter: Whether Hunter.io key is required

        Returns:
            List of missing key names (empty if all present)
        """
        missing: list[str] = []

        if not self.google_places_api_key.get_secret_value():
            missing.append("GOOGLE_PLACES_API_KEY")
        if not self.openai_api_key.get_secret_value():
            missing.append("OPENAI_API_KEY")
        if not self.google_service_account_path and not self.google_service_account_base64.get_secret_value():
            missing.append("GOOGLE_SERVICE_ACCOUNT_PATH or GOOGLE_SERVICE_ACCOUNT_BASE64")
        if require_hunter and not self.hunter_api_key.get_secret_value():
            missing.append("HUNTER_API_KEY")

        return missing


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached application settings.

    Settings are loaded once and cached for performance.
    Use this function instead of creating Settings() directly.

    Returns:
        Cached Settings instance
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Reload settings (clears cache).

    Use this after modifying environment variables.

    Returns:
        Fresh Settings instance
    """
    get_settings.cache_clear()
    return get_settings()
