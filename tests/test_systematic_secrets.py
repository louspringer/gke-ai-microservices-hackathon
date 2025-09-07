"""Tests for systematic secrets management."""

import pytest
import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.beast_mode.systematic_secrets.core.secrets_manager import SecretsManager, SecretsManagerConfig
from src.beast_mode.systematic_secrets.backends.local_adapter import LocalAdapter
from src.beast_mode.systematic_secrets.models.secret import Secret, SecretType, SecretMetadata
from src.beast_mode.systematic_secrets.models.environment import Environment, EnvironmentType, EnvironmentSecurity


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def secrets_manager(temp_storage):
    """Create a configured secrets manager."""
    config = SecretsManagerConfig(
        default_backend="local",
        cache_enabled=True,
        cache_ttl_seconds=60
    )
    
    manager = SecretsManager(config)
    
    # Register local backend
    local_backend = LocalAdapter({
        'storage_path': str(temp_storage),
        'backup_enabled': True
    })
    manager.register_backend("local", local_backend)
    
    # Initialize
    await manager.initialize()
    
    return manager


@pytest.fixture
def sample_secret():
    """Create a sample secret for testing."""
    metadata = SecretMetadata(
        created_at=datetime.utcnow(),
        created_by="test_user",
        description="Test secret"
    )
    
    return Secret(
        name="test_api_key",
        secret_type=SecretType.API_KEY,
        environment="development",
        value="test_secret_value_123",
        metadata=metadata
    )


class TestSecretsManager:
    """Test cases for SecretsManager."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, secrets_manager):
        """Test secrets manager initialization."""
        assert secrets_manager.is_healthy()
        assert secrets_manager.get_module_status().value in ["healthy", "initializing"]
        
        # Check that default environments are created
        operational_info = secrets_manager.get_operational_info()
        assert "development" in operational_info['environments']
        assert "production" in operational_info['environments']
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret(self, secrets_manager, sample_secret):
        """Test storing and retrieving a secret."""
        # Store the secret
        success = await secrets_manager.store_secret(sample_secret, "development")
        assert success
        
        # Retrieve the secret
        retrieved = await secrets_manager.retrieve_secret(sample_secret.id, "development")
        assert retrieved is not None
        assert retrieved.name == sample_secret.name
        assert retrieved.value == sample_secret.value
        assert retrieved.secret_type == sample_secret.secret_type
    
    @pytest.mark.asyncio
    async def test_environment_isolation(self, secrets_manager, sample_secret):
        """Test that environment isolation works."""
        # Store secret in development
        await secrets_manager.store_secret(sample_secret, "development")
        
        # Try to retrieve from production (should not find it)
        retrieved = await secrets_manager.retrieve_secret(sample_secret.id, "production")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_secret_rotation(self, secrets_manager, sample_secret):
        """Test secret rotation."""
        # Store the secret
        await secrets_manager.store_secret(sample_secret, "development")
        
        # Rotate the secret
        new_value = "new_rotated_value_456"
        success = await secrets_manager.rotate_secret(sample_secret.id, new_value, "development")
        assert success
        
        # Retrieve and verify rotation
        rotated = await secrets_manager.retrieve_secret(sample_secret.id, "development")
        assert rotated is not None
        assert rotated.value == new_value
        assert rotated.metadata.rotation_count == 1
        assert rotated.metadata.last_rotated is not None
    
    @pytest.mark.asyncio
    async def test_list_secrets(self, secrets_manager, sample_secret):
        """Test listing secrets."""
        # Store multiple secrets
        secret1 = sample_secret
        secret2 = Secret(
            name="test_db_password",
            secret_type=SecretType.DATABASE_PASSWORD,
            environment="development",
            value="db_password_123",
            metadata=SecretMetadata(
                created_at=datetime.utcnow(),
                created_by="test_user"
            )
        )
        
        await secrets_manager.store_secret(secret1, "development")
        await secrets_manager.store_secret(secret2, "development")
        
        # List all secrets
        secrets = await secrets_manager.list_secrets("development")
        assert len(secrets) == 2
        
        # List with filters
        api_secrets = await secrets_manager.list_secrets(
            "development", 
            filters={'secret_type': SecretType.API_KEY}
        )
        assert len(api_secrets) == 1
        assert api_secrets[0].name == "test_api_key"
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, secrets_manager, sample_secret):
        """Test caching functionality."""
        # Store secret
        await secrets_manager.store_secret(sample_secret, "development")
        
        # First retrieval (cache miss)
        retrieved1 = await secrets_manager.retrieve_secret(sample_secret.id, "development")
        assert retrieved1 is not None
        
        # Second retrieval (cache hit)
        retrieved2 = await secrets_manager.retrieve_secret(sample_secret.id, "development")
        assert retrieved2 is not None
        
        # Check metrics
        metrics = secrets_manager._metrics
        assert metrics['cache_hits'] > 0
        assert metrics['cache_misses'] > 0
    
    @pytest.mark.asyncio
    async def test_health_indicators(self, secrets_manager):
        """Test health indicators."""
        indicators = secrets_manager.get_health_indicators()
        
        # Should have backend, cache, and metrics indicators
        indicator_names = [ind.name for ind in indicators]
        assert "backend_local" in indicator_names
        assert "cache" in indicator_names
        assert "metrics" in indicator_names
        
        # All should be healthy
        for indicator in indicators:
            assert indicator.status == "healthy"
    
    @pytest.mark.asyncio
    async def test_operational_info(self, secrets_manager):
        """Test operational information."""
        info = secrets_manager.get_operational_info()
        
        assert info['module_name'] == 'SecretsManager'
        assert 'local' in info['backends']
        assert 'development' in info['environments']
        assert 'metrics' in info
        assert 'config' in info
    
    @pytest.mark.asyncio
    async def test_documentation_compliance(self, secrets_manager):
        """Test documentation compliance."""
        compliance = secrets_manager.get_documentation_compliance()
        
        assert compliance['has_docstrings'] is True
        assert compliance['has_type_hints'] is True
        assert compliance['documentation_coverage'] > 90
        assert 'api_documentation' in compliance


class TestLocalAdapter:
    """Test cases for LocalAdapter."""
    
    @pytest.fixture
    async def local_adapter(self, temp_storage):
        """Create a local adapter for testing."""
        adapter = LocalAdapter({
            'storage_path': str(temp_storage),
            'backup_enabled': True
        })
        await adapter.initialize()
        return adapter
    
    @pytest.fixture
    def test_environment(self):
        """Create a test environment."""
        return Environment(
            name="test",
            display_name="Test Environment",
            environment_type=EnvironmentType.TESTING,
            security_level=EnvironmentSecurity.LOW
        )
    
    @pytest.mark.asyncio
    async def test_health_check(self, local_adapter):
        """Test backend health check."""
        health = await local_adapter.health_check()
        
        assert health['status'] == 'healthy'
        assert 'response_time_ms' in health
        assert health['details']['writable'] is True
        assert health['details']['encryption_enabled'] is True
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, local_adapter, test_environment, sample_secret):
        """Test storing and retrieving secrets."""
        # Store secret
        success = await local_adapter.store_secret(sample_secret, test_environment)
        assert success
        
        # Retrieve secret
        retrieved = await local_adapter.retrieve_secret(sample_secret.id, test_environment)
        assert retrieved is not None
        assert retrieved.name == sample_secret.name
        assert retrieved.value == sample_secret.value
    
    @pytest.mark.asyncio
    async def test_encryption(self, local_adapter, test_environment, sample_secret):
        """Test that secrets are encrypted on disk."""
        # Store secret
        await local_adapter.store_secret(sample_secret, test_environment)
        
        # Check that the file exists and is encrypted
        secret_file = local_adapter.storage_path / test_environment.name / f"{sample_secret.id}.json"
        assert secret_file.exists()
        
        # Read raw file content - should be encrypted (not readable as JSON)
        with open(secret_file, 'rb') as f:
            raw_content = f.read()
        
        # Should not contain the plain text secret value
        assert sample_secret.value.encode() not in raw_content
    
    @pytest.mark.asyncio
    async def test_secret_versions(self, local_adapter, test_environment, sample_secret):
        """Test secret version tracking."""
        # Store secret
        await local_adapter.store_secret(sample_secret, test_environment)
        
        # Get versions
        versions = await local_adapter.get_secret_versions(sample_secret.id, test_environment)
        assert len(versions) == 1
        assert versions[0]['version'] == 1
        assert versions[0]['rotation_count'] == 0


if __name__ == "__main__":
    pytest.main([__file__])