"""
Comprehensive unit tests for secret management module.

Tests cover:
- EnvSecretBackend (get existing/missing secrets)
- VaultSecretBackend initialization and operations
- AWSSecretBackend initialization and operations
- SecretManager with different backends
- get_secret_manager singleton
- Secret caching behavior
- Secret expiration
- Health checks
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from lead_gen.core.config import SecretBackend, Settings
from lead_gen.core.exceptions import ConfigurationError, SecurityError
from lead_gen.core.secrets import (
    AWSSecretBackend,
    EnvSecretBackend,
    SecretManager,
    SecretValue,
    VaultSecretBackend,
    get_secret_manager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    # Clear any existing test secrets
    for key in list(os.environ.keys()):
        if key.startswith("TEST_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def env_backend():
    """Create an EnvSecretBackend instance."""
    return EnvSecretBackend(prefix="TEST_")


@pytest.fixture
def mock_vault_client():
    """Mock hvac.Client for Vault testing."""
    mock = MagicMock()
    mock.is_authenticated.return_value = True
    mock.secrets.kv.v2.read_secret_version.return_value = {
        "data": {
            "data": {
                "API_KEY": "vault-secret-value",
                "DB_PASSWORD": "vault-db-pass",
            }
        }
    }
    return mock


@pytest.fixture
def mock_aws_client():
    """Mock boto3.client for AWS testing."""
    mock = MagicMock()
    mock.get_secret_value.return_value = {
        "SecretString": '{"API_KEY": "aws-secret-value", "DB_PASSWORD": "aws-db-pass"}'
    }
    return mock


@pytest.fixture
def secret_manager_with_env():
    """Create SecretManager with EnvSecretBackend."""
    backend = EnvSecretBackend()
    return SecretManager(backend)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the global secret manager singleton before each test."""
    import lead_gen.core.secrets
    lead_gen.core.secrets._secret_manager = None
    yield
    lead_gen.core.secrets._secret_manager = None


# ============================================================================
# SecretValue Tests
# ============================================================================


class TestSecretValue:
    """Test SecretValue dataclass and expiration logic."""

    def test_secret_value_creation(self):
        """Test SecretValue can be created with required fields."""
        secret = SecretValue(
            value="test-secret",
            key="API_KEY",
            backend="EnvSecretBackend",
        )
        assert secret.value == "test-secret"
        assert secret.key == "API_KEY"
        assert secret.backend == "EnvSecretBackend"
        assert secret.fetched_at is not None

    def test_secret_value_not_expired_by_default(self):
        """Test SecretValue without expires_at is never expired."""
        secret = SecretValue(
            value="test-secret",
            key="API_KEY",
            backend="EnvSecretBackend",
        )
        assert not secret.is_expired()

    def test_secret_value_expired_when_past_expiration(self):
        """Test SecretValue is expired when expires_at is in the past."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        secret = SecretValue(
            value="test-secret",
            key="API_KEY",
            backend="EnvSecretBackend",
            expires_at=past_time,
        )
        assert secret.is_expired()

    def test_secret_value_not_expired_when_future_expiration(self):
        """Test SecretValue is not expired when expires_at is in the future."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        secret = SecretValue(
            value="test-secret",
            key="API_KEY",
            backend="EnvSecretBackend",
            expires_at=future_time,
        )
        assert not secret.is_expired()

    def test_secret_value_repr(self):
        """Test SecretValue __repr__ doesn't expose the secret value."""
        secret = SecretValue(
            value="test-secret",
            key="API_KEY",
            backend="EnvSecretBackend",
        )
        repr_str = repr(secret)
        assert "API_KEY" in repr_str
        assert "EnvSecretBackend" in repr_str
        assert "test-secret" not in repr_str  # Value should not be in repr


# ============================================================================
# EnvSecretBackend Tests
# ============================================================================


class TestEnvSecretBackend:
    """Test environment variable secret backend."""

    @pytest.mark.asyncio
    async def test_get_existing_secret(self, monkeypatch):
        """Test EnvSecretBackend retrieves existing environment variable."""
        monkeypatch.setenv("TEST_API_KEY", "my-secret-value")
        backend = EnvSecretBackend(prefix="TEST_")

        value = await backend.get_secret("API_KEY")

        assert value == "my-secret-value"

    @pytest.mark.asyncio
    async def test_get_missing_secret_returns_empty(self, clean_env):
        """Test EnvSecretBackend returns empty string for missing secret."""
        backend = EnvSecretBackend(prefix="TEST_")

        value = await backend.get_secret("NONEXISTENT_KEY")

        assert value == ""

    @pytest.mark.asyncio
    async def test_get_secret_without_prefix(self, monkeypatch):
        """Test EnvSecretBackend works without prefix."""
        monkeypatch.setenv("API_KEY", "no-prefix-value")
        backend = EnvSecretBackend(prefix="")

        value = await backend.get_secret("API_KEY")

        assert value == "no-prefix-value"

    @pytest.mark.asyncio
    async def test_get_secrets_multiple(self, monkeypatch):
        """Test EnvSecretBackend retrieves multiple secrets."""
        monkeypatch.setenv("TEST_KEY1", "value1")
        monkeypatch.setenv("TEST_KEY2", "value2")
        monkeypatch.setenv("TEST_KEY3", "value3")
        backend = EnvSecretBackend(prefix="TEST_")

        values = await backend.get_secrets(["KEY1", "KEY2", "KEY3"])

        assert values == {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
        }

    @pytest.mark.asyncio
    async def test_get_secrets_with_missing(self, monkeypatch):
        """Test get_secrets handles missing keys gracefully."""
        monkeypatch.setenv("TEST_KEY1", "value1")
        backend = EnvSecretBackend(prefix="TEST_")

        values = await backend.get_secrets(["KEY1", "MISSING_KEY"])

        assert values == {
            "KEY1": "value1",
            "MISSING_KEY": "",
        }

    @pytest.mark.asyncio
    async def test_health_check_always_healthy(self):
        """Test EnvSecretBackend health check always returns True."""
        backend = EnvSecretBackend()

        is_healthy = await backend.health_check()

        assert is_healthy is True


# ============================================================================
# VaultSecretBackend Tests
# ============================================================================


class TestVaultSecretBackend:
    """Test HashiCorp Vault secret backend."""

    def test_initialization(self):
        """Test VaultSecretBackend can be initialized."""
        backend = VaultSecretBackend(
            addr="https://vault.example.com",
            token="test-token",
            mount_point="secret",
            secret_path="myapp/keys",
        )

        assert backend.addr == "https://vault.example.com"
        assert backend.token == "test-token"
        assert backend.mount_point == "secret"
        assert backend.secret_path == "myapp/keys"
        assert backend._client is None  # Lazy initialization

    @pytest.mark.asyncio
    async def test_get_secret_success(self, mock_vault_client):
        """Test VaultSecretBackend retrieves secret successfully."""
        with patch("hvac.Client", return_value=mock_vault_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="test-token",
            )

            value = await backend.get_secret("API_KEY")

            assert value == "vault-secret-value"
            mock_vault_client.secrets.kv.v2.read_secret_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_secret_missing(self, mock_vault_client):
        """Test VaultSecretBackend handles missing secret."""
        mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {}}
        }

        with patch("hvac.Client", return_value=mock_vault_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="test-token",
            )

            value = await backend.get_secret("MISSING_KEY")

            assert value == ""

    @pytest.mark.asyncio
    async def test_get_secret_vault_error(self, mock_vault_client):
        """Test VaultSecretBackend raises SecurityError on Vault errors."""
        mock_vault_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Vault error")

        with patch("hvac.Client", return_value=mock_vault_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="test-token",
            )

            with pytest.raises(SecurityError) as exc_info:
                await backend.get_secret("API_KEY")

            assert "Failed to retrieve secret from Vault" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test VaultSecretBackend raises SecurityError on auth failure."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False

        with patch("hvac.Client", return_value=mock_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="bad-token",
            )

            with pytest.raises(SecurityError) as exc_info:
                backend._get_client()

            assert "Vault authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hvac_not_installed(self):
        """Test VaultSecretBackend raises ConfigurationError if hvac not installed."""
        import builtins
        orig_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'hvac':
                raise ImportError("No module named 'hvac'")
            return orig_import(name, *args, **kwargs)

        backend = VaultSecretBackend(
            addr="https://vault.example.com",
            token="test-token",
        )
        backend._client = None  # Reset any cached client

        with patch.object(builtins, '__import__', side_effect=mock_import):
            with pytest.raises(ConfigurationError) as exc_info:
                backend._get_client()

        assert "hvac package required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_secrets_multiple(self, mock_vault_client):
        """Test VaultSecretBackend retrieves multiple secrets in one call."""
        with patch("hvac.Client", return_value=mock_vault_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="test-token",
            )

            values = await backend.get_secrets(["API_KEY", "DB_PASSWORD"])

            assert values == {
                "API_KEY": "vault-secret-value",
                "DB_PASSWORD": "vault-db-pass",
            }
            # Should only make one API call
            assert mock_vault_client.secrets.kv.v2.read_secret_version.call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_vault_client):
        """Test VaultSecretBackend health check when authenticated."""
        with patch("hvac.Client", return_value=mock_vault_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="test-token",
            )

            is_healthy = await backend.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test VaultSecretBackend health check when not authenticated."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False

        with patch("hvac.Client", return_value=mock_client):
            backend = VaultSecretBackend(
                addr="https://vault.example.com",
                token="bad-token",
            )

            is_healthy = await backend.health_check()

            assert is_healthy is False


# ============================================================================
# AWSSecretBackend Tests
# ============================================================================


class TestAWSSecretBackend:
    """Test AWS Secrets Manager backend."""

    def test_initialization(self):
        """Test AWSSecretBackend can be initialized."""
        backend = AWSSecretBackend(
            region="us-west-2",
            secret_name="myapp/secrets",
        )

        assert backend.region == "us-west-2"
        assert backend.secret_name == "myapp/secrets"
        assert backend._client is None  # Lazy initialization
        assert backend._cache == {}

    @pytest.mark.asyncio
    async def test_get_secret_success(self, mock_aws_client):
        """Test AWSSecretBackend retrieves secret successfully."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            value = await backend.get_secret("API_KEY")

            assert value == "aws-secret-value"
            mock_aws_client.get_secret_value.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_secret_missing(self, mock_aws_client):
        """Test AWSSecretBackend handles missing secret key."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            value = await backend.get_secret("MISSING_KEY")

            assert value == ""

    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_aws_client):
        """Test AWSSecretBackend caches secrets for TTL period."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )
            backend._cache_ttl = timedelta(minutes=5)

            # First call fetches from AWS
            value1 = await backend.get_secret("API_KEY")
            # Second call uses cache
            value2 = await backend.get_secret("API_KEY")

            assert value1 == value2
            # Should only call AWS once
            assert mock_aws_client.get_secret_value.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self, mock_aws_client):
        """Test AWSSecretBackend refetches after cache TTL expires."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )
            backend._cache_ttl = timedelta(seconds=0)  # Immediate expiration

            # First call
            await backend.get_secret("API_KEY")
            # Second call after expiration
            await backend.get_secret("API_KEY")

            # Should call AWS twice
            assert mock_aws_client.get_secret_value.call_count == 2

    @pytest.mark.asyncio
    async def test_aws_error(self, mock_aws_client):
        """Test AWSSecretBackend raises SecurityError on AWS errors."""
        mock_aws_client.get_secret_value.side_effect = Exception("AWS error")

        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            with pytest.raises(SecurityError) as exc_info:
                await backend.get_secret("API_KEY")

            assert "Failed to retrieve secret from AWS" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_boto3_not_installed(self):
        """Test AWSSecretBackend raises ConfigurationError if boto3 not installed."""
        import builtins
        orig_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'boto3':
                raise ImportError("No module named 'boto3'")
            return orig_import(name, *args, **kwargs)

        backend = AWSSecretBackend(
            region="us-west-2",
            secret_name="myapp/secrets",
        )
        backend._client = None  # Reset any cached client

        with patch.object(builtins, '__import__', side_effect=mock_import):
            with pytest.raises(ConfigurationError) as exc_info:
                backend._get_client()

        assert "boto3 package required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_secrets_multiple(self, mock_aws_client):
        """Test AWSSecretBackend retrieves multiple secrets."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            values = await backend.get_secrets(["API_KEY", "DB_PASSWORD"])

            assert values == {
                "API_KEY": "aws-secret-value",
                "DB_PASSWORD": "aws-db-pass",
            }

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_aws_client):
        """Test AWSSecretBackend health check succeeds."""
        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            is_healthy = await backend.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_aws_client):
        """Test AWSSecretBackend health check fails on error."""
        mock_aws_client.get_secret_value.side_effect = Exception("Connection error")

        with patch("boto3.client", return_value=mock_aws_client):
            backend = AWSSecretBackend(
                region="us-west-2",
                secret_name="myapp/secrets",
            )

            is_healthy = await backend.health_check()

            assert is_healthy is False


# ============================================================================
# SecretManager Tests
# ============================================================================


class TestSecretManager:
    """Test unified SecretManager with caching."""

    @pytest.mark.asyncio
    async def test_create_with_env_backend(self):
        """Test SecretManager.create() uses EnvSecretBackend by default."""
        settings = Mock(spec=Settings)
        settings.secret_backend = SecretBackend.ENV

        manager = await SecretManager.create(settings)

        assert isinstance(manager._backend, EnvSecretBackend)

    @pytest.mark.asyncio
    async def test_create_with_vault_backend(self, mock_vault_client):
        """Test SecretManager.create() with VaultSecretBackend."""
        settings = Mock(spec=Settings)
        settings.secret_backend = SecretBackend.VAULT
        settings.vault = Mock()
        settings.vault.addr = "https://vault.example.com"
        settings.vault.token = Mock()
        settings.vault.token.get_secret_value.return_value = "test-token"
        settings.vault.mount_point = "secret"
        settings.vault.secret_path = "myapp/keys"

        with patch("hvac.Client", return_value=mock_vault_client):
            manager = await SecretManager.create(settings)

            assert isinstance(manager._backend, VaultSecretBackend)

    @pytest.mark.asyncio
    async def test_create_with_aws_backend(self, mock_aws_client):
        """Test SecretManager.create() with AWSSecretBackend."""
        settings = Mock(spec=Settings)
        settings.secret_backend = SecretBackend.AWS_SECRETS_MANAGER
        settings.aws = Mock()
        settings.aws.region = "us-west-2"
        settings.aws.secret_name = "myapp/secrets"

        with patch("boto3.client", return_value=mock_aws_client):
            manager = await SecretManager.create(settings)

            assert isinstance(manager._backend, AWSSecretBackend)

    @pytest.mark.asyncio
    async def test_get_with_caching(self, monkeypatch, secret_manager_with_env):
        """Test SecretManager caches secrets."""
        monkeypatch.setenv("API_KEY", "cached-value")
        manager = secret_manager_with_env

        # First call fetches from backend
        value1 = await manager.get("API_KEY")

        # Change env var
        monkeypatch.setenv("API_KEY", "new-value")

        # Second call uses cache
        value2 = await manager.get("API_KEY")

        assert value1 == "cached-value"
        assert value2 == "cached-value"  # Still cached

    @pytest.mark.asyncio
    async def test_get_cache_expiration(self, monkeypatch, secret_manager_with_env):
        """Test SecretManager refetches after cache expires."""
        monkeypatch.setenv("API_KEY", "initial-value")
        manager = secret_manager_with_env
        manager._cache_ttl = timedelta(seconds=0)  # Immediate expiration

        # First call
        value1 = await manager.get("API_KEY")

        # Change env var
        monkeypatch.setenv("API_KEY", "updated-value")

        # Second call after expiration
        value2 = await manager.get("API_KEY")

        assert value1 == "initial-value"
        assert value2 == "updated-value"

    @pytest.mark.asyncio
    async def test_get_with_default(self, secret_manager_with_env):
        """Test SecretManager returns default for missing secret."""
        manager = secret_manager_with_env

        value = await manager.get("NONEXISTENT", default="fallback-value")

        assert value == "fallback-value"

    @pytest.mark.asyncio
    async def test_get_many(self, monkeypatch, secret_manager_with_env):
        """Test SecretManager.get_many() retrieves multiple secrets."""
        monkeypatch.setenv("KEY1", "value1")
        monkeypatch.setenv("KEY2", "value2")
        monkeypatch.setenv("KEY3", "value3")
        manager = secret_manager_with_env

        values = await manager.get_many(["KEY1", "KEY2", "KEY3"])

        assert values == {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
        }

    @pytest.mark.asyncio
    async def test_get_many_with_partial_cache(self, monkeypatch, secret_manager_with_env):
        """Test get_many() uses cached values and fetches missing ones."""
        monkeypatch.setenv("KEY1", "value1")
        monkeypatch.setenv("KEY2", "value2")
        manager = secret_manager_with_env

        # Cache KEY1
        await manager.get("KEY1")

        # Get both keys
        values = await manager.get_many(["KEY1", "KEY2"])

        assert values == {
            "KEY1": "value1",
            "KEY2": "value2",
        }

    @pytest.mark.asyncio
    async def test_clear_cache(self, monkeypatch, secret_manager_with_env):
        """Test SecretManager.clear_cache() clears all cached secrets."""
        monkeypatch.setenv("API_KEY", "initial-value")
        manager = secret_manager_with_env

        # Cache a secret
        await manager.get("API_KEY")
        assert len(manager._cache) == 1

        # Clear cache
        manager.clear_cache()

        assert len(manager._cache) == 0

    @pytest.mark.asyncio
    async def test_health_check(self, secret_manager_with_env):
        """Test SecretManager.health_check() delegates to backend."""
        manager = secret_manager_with_env

        is_healthy = await manager.health_check()

        assert is_healthy is True


# ============================================================================
# Singleton Tests
# ============================================================================


class TestGetSecretManager:
    """Test get_secret_manager singleton function."""

    @pytest.mark.asyncio
    async def test_get_secret_manager_creates_instance(self):
        """Test get_secret_manager creates and returns instance."""
        manager = await get_secret_manager()

        assert manager is not None
        assert isinstance(manager, SecretManager)

    @pytest.mark.asyncio
    async def test_get_secret_manager_returns_same_instance(self):
        """Test get_secret_manager returns same instance on multiple calls."""
        manager1 = await get_secret_manager()
        manager2 = await get_secret_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_singleton_reset(self, reset_singleton):
        """Test singleton can be reset for testing."""
        manager1 = await get_secret_manager()

        # Reset (done by fixture)
        import lead_gen.core.secrets
        lead_gen.core.secrets._secret_manager = None

        manager2 = await get_secret_manager()

        assert manager1 is not manager2
