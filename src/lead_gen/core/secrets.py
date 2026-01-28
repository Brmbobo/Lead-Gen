"""
Enterprise secret management with support for multiple backends.

Supports:
- Environment variables (development)
- HashiCorp Vault (production)
- AWS Secrets Manager (cloud)

Secrets are cached and refreshed periodically.
"""

from __future__ import annotations

import base64
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import structlog

from lead_gen.core.config import SecretBackend, Settings, get_settings
from lead_gen.core.exceptions import ConfigurationError, SecurityError

logger = structlog.get_logger(__name__)


@dataclass
class SecretValue:
    """Wrapper for a secret value with metadata."""

    value: str
    key: str
    backend: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the secret has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def __repr__(self) -> str:
        return f"SecretValue(key={self.key!r}, backend={self.backend!r}, expired={self.is_expired()})"


class SecretBackendBase(ABC):
    """Base class for secret backends."""

    @abstractmethod
    async def get_secret(self, key: str) -> str:
        """Retrieve a secret by key."""
        ...

    @abstractmethod
    async def get_secrets(self, keys: list[str]) -> dict[str, str]:
        """Retrieve multiple secrets at once."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy."""
        ...


class EnvSecretBackend(SecretBackendBase):
    """
    Environment variable secret backend.

    Simple backend for development that reads from environment variables.
    """

    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix

    async def get_secret(self, key: str) -> str:
        """Get secret from environment variable."""
        env_key = f"{self.prefix}{key}".upper()
        value = os.environ.get(env_key, "")

        if not value:
            logger.warning("secret_not_found", key=env_key, backend="env")

        return value

    async def get_secrets(self, keys: list[str]) -> dict[str, str]:
        """Get multiple secrets from environment."""
        return {key: await self.get_secret(key) for key in keys}

    async def health_check(self) -> bool:
        """Environment backend is always healthy."""
        return True


class VaultSecretBackend(SecretBackendBase):
    """
    HashiCorp Vault secret backend.

    Production-ready secret management with:
    - Token authentication
    - Secret versioning
    - Automatic renewal
    """

    def __init__(
        self,
        addr: str,
        token: str,
        mount_point: str = "secret",
        secret_path: str = "lead-gen/api-keys",
    ) -> None:
        self.addr = addr
        self.token = token
        self.mount_point = mount_point
        self.secret_path = secret_path
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of Vault client."""
        if self._client is None:
            try:
                import hvac

                self._client = hvac.Client(url=self.addr, token=self.token)
                if not self._client.is_authenticated():
                    raise SecurityError(
                        "Vault authentication failed",
                        threat_type="authentication_failure",
                    )
            except ImportError:
                raise ConfigurationError(
                    "hvac package required for Vault backend. Install with: pip install hvac",
                    config_key="SECRET_BACKEND",
                )
        return self._client

    async def get_secret(self, key: str) -> str:
        """Get a secret from Vault."""
        try:
            client = self._get_client()
            response = client.secrets.kv.v2.read_secret_version(
                path=self.secret_path,
                mount_point=self.mount_point,
            )
            data = response.get("data", {}).get("data", {})
            value = data.get(key, "")

            if not value:
                logger.warning("secret_not_found", key=key, backend="vault")

            return value

        except Exception as e:
            logger.error("vault_secret_error", key=key, error=str(e))
            raise SecurityError(
                f"Failed to retrieve secret from Vault: {e}",
                threat_type="secret_retrieval_failure",
                cause=e,
            )

    async def get_secrets(self, keys: list[str]) -> dict[str, str]:
        """Get multiple secrets from Vault (single API call)."""
        try:
            client = self._get_client()
            response = client.secrets.kv.v2.read_secret_version(
                path=self.secret_path,
                mount_point=self.mount_point,
            )
            data = response.get("data", {}).get("data", {})
            return {key: data.get(key, "") for key in keys}

        except Exception as e:
            logger.error("vault_secrets_error", error=str(e))
            raise SecurityError(
                f"Failed to retrieve secrets from Vault: {e}",
                threat_type="secret_retrieval_failure",
                cause=e,
            )

    async def health_check(self) -> bool:
        """Check Vault connectivity and authentication."""
        try:
            client = self._get_client()
            return client.is_authenticated()
        except Exception:
            return False


class AWSSecretBackend(SecretBackendBase):
    """
    AWS Secrets Manager backend.

    Cloud-native secret management with:
    - IAM authentication
    - Automatic rotation support
    - Regional deployment
    """

    def __init__(self, region: str, secret_name: str) -> None:
        self.region = region
        self.secret_name = secret_name
        self._client: Any = None
        self._cache: dict[str, str] = {}
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(minutes=5)

    def _get_client(self) -> Any:
        """Lazy initialization of AWS client."""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.region,
                )
            except ImportError:
                raise ConfigurationError(
                    "boto3 package required for AWS backend. Install with: pip install boto3",
                    config_key="SECRET_BACKEND",
                )
        return self._client

    async def _fetch_all_secrets(self) -> dict[str, str]:
        """Fetch all secrets from AWS (with caching)."""
        now = datetime.now(timezone.utc)

        # Return cache if valid
        if self._cache_time and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=self.secret_name)
            secret_string = response.get("SecretString", "{}")
            self._cache = json.loads(secret_string)
            self._cache_time = now
            return self._cache

        except Exception as e:
            logger.error("aws_secret_error", error=str(e))
            raise SecurityError(
                f"Failed to retrieve secret from AWS: {e}",
                threat_type="secret_retrieval_failure",
                cause=e,
            )

    async def get_secret(self, key: str) -> str:
        """Get a secret from AWS Secrets Manager."""
        secrets = await self._fetch_all_secrets()
        value = secrets.get(key, "")

        if not value:
            logger.warning("secret_not_found", key=key, backend="aws")

        return value

    async def get_secrets(self, keys: list[str]) -> dict[str, str]:
        """Get multiple secrets from AWS."""
        secrets = await self._fetch_all_secrets()
        return {key: secrets.get(key, "") for key in keys}

    async def health_check(self) -> bool:
        """Check AWS connectivity."""
        try:
            await self._fetch_all_secrets()
            return True
        except Exception:
            return False


class SecretManager:
    """
    Unified secret manager with caching and backend abstraction.

    Provides a single interface for all secret backends with:
    - Automatic backend selection based on configuration
    - In-memory caching with TTL
    - Fallback support
    - Audit logging

    Example:
        >>> manager = await SecretManager.create()
        >>> api_key = await manager.get("OPENAI_API_KEY")
    """

    def __init__(self, backend: SecretBackendBase) -> None:
        self._backend = backend
        self._cache: dict[str, SecretValue] = {}
        self._cache_ttl = timedelta(minutes=5)

    @classmethod
    async def create(cls, settings: Settings | None = None) -> "SecretManager":
        """Create a SecretManager with the configured backend."""
        if settings is None:
            settings = get_settings()

        backend: SecretBackendBase

        if settings.secret_backend == SecretBackend.VAULT:
            backend = VaultSecretBackend(
                addr=settings.vault.addr,
                token=settings.vault.token.get_secret_value(),
                mount_point=settings.vault.mount_point,
                secret_path=settings.vault.secret_path,
            )
        elif settings.secret_backend == SecretBackend.AWS_SECRETS_MANAGER:
            backend = AWSSecretBackend(
                region=settings.aws.region,
                secret_name=settings.aws.secret_name,
            )
        else:
            backend = EnvSecretBackend()

        manager = cls(backend)

        # Health check
        if not await backend.health_check():
            logger.warning(
                "secret_backend_unhealthy",
                backend=settings.secret_backend.value,
            )

        logger.info(
            "secret_manager_initialized",
            backend=settings.secret_backend.value,
        )

        return manager

    async def get(self, key: str, default: str = "") -> str:
        """
        Get a secret by key.

        Args:
            key: Secret key name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        # Check cache
        if key in self._cache:
            cached = self._cache[key]
            if not cached.is_expired():
                return cached.value
            del self._cache[key]

        # Fetch from backend
        value = await self._backend.get_secret(key)

        if value:
            self._cache[key] = SecretValue(
                value=value,
                key=key,
                backend=self._backend.__class__.__name__,
                expires_at=datetime.now(timezone.utc) + self._cache_ttl,
            )
            logger.debug("secret_fetched", key=key)
            return value

        return default

    async def get_many(self, keys: list[str]) -> dict[str, str]:
        """Get multiple secrets at once."""
        # Check cache first
        result: dict[str, str] = {}
        missing: list[str] = []

        for key in keys:
            if key in self._cache and not self._cache[key].is_expired():
                result[key] = self._cache[key].value
            else:
                missing.append(key)

        # Fetch missing from backend
        if missing:
            fetched = await self._backend.get_secrets(missing)
            now = datetime.now(timezone.utc)

            for key, value in fetched.items():
                if value:
                    self._cache[key] = SecretValue(
                        value=value,
                        key=key,
                        backend=self._backend.__class__.__name__,
                        expires_at=now + self._cache_ttl,
                    )
                result[key] = value

        return result

    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self._cache.clear()
        logger.info("secret_cache_cleared")

    async def health_check(self) -> bool:
        """Check backend health."""
        return await self._backend.health_check()


# Global secret manager instance
_secret_manager: SecretManager | None = None


async def get_secret_manager() -> SecretManager:
    """Get or create the global secret manager."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = await SecretManager.create()
    return _secret_manager


def decode_service_account(base64_or_path: str) -> dict[str, Any]:
    """
    Decode a Google service account from base64 or file path.

    Args:
        base64_or_path: Base64 encoded JSON or file path

    Returns:
        Parsed service account dictionary
    """
    # Try as file path first
    if os.path.exists(base64_or_path):
        with open(base64_or_path) as f:
            return json.load(f)

    # Try as base64
    try:
        decoded = base64.b64decode(base64_or_path)
        return json.loads(decoded)
    except Exception:
        pass

    # Try as raw JSON
    try:
        return json.loads(base64_or_path)
    except Exception:
        raise ConfigurationError(
            "Invalid service account: not a valid file path, base64, or JSON",
            config_key="GOOGLE_SERVICE_ACCOUNT",
        )
