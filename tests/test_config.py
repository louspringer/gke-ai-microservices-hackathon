"""Tests for configuration management system."""

import pytest
import tempfile
import yaml
from pathlib import Path
from gke_local.config.manager import ConfigManager
from gke_local.config.models import GKELocalConfig, LogLevel


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            manager = ConfigManager(config_dir)
            
            # Should create default config and load it
            config = manager.load_config()
            
            assert config.project_name == "my-gke-local-project"
            assert config.environment == "local"
            assert config.cluster.name == "local-gke-dev"
            assert config.simulation.cloud_run.enabled is True
    
    def test_load_custom_config(self):
        """Test loading custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "gke-local.yaml"
            
            # Create custom config
            custom_config = {
                "project_name": "test-project",
                "log_level": "debug",
                "cluster": {
                    "nodes": 5
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(custom_config, f)
            
            manager = ConfigManager(config_dir)
            config = manager.load_config()
            
            assert config.project_name == "test-project"
            assert config.log_level == LogLevel.DEBUG
            assert config.cluster.nodes == 5
    
    def test_environment_override(self):
        """Test environment-specific configuration override."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create base config
            base_config = {
                "project_name": "test-project",
                "cluster": {"nodes": 3}
            }
            with open(config_dir / "gke-local.yaml", 'w') as f:
                yaml.dump(base_config, f)
            
            # Create staging override
            staging_config = {
                "cluster": {"nodes": 10},
                "log_level": "warning"
            }
            with open(config_dir / "gke-local.staging.yaml", 'w') as f:
                yaml.dump(staging_config, f)
            
            manager = ConfigManager(config_dir)
            config = manager.load_config("staging")
            
            assert config.project_name == "test-project"  # From base
            assert config.cluster.nodes == 10  # From override
            assert config.log_level == LogLevel.WARNING  # From override
            assert config.environment == "staging"  # Set by load_config
    
    def test_config_validation(self):
        """Test configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "gke-local.yaml"
            
            # Create invalid config
            invalid_config = {
                "project_name": "invalid name with spaces",  # Invalid
                "cluster": {
                    "kubernetes_version": "invalid"  # Invalid format
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(invalid_config, f)
            
            manager = ConfigManager(config_dir)
            
            with pytest.raises(ValueError):
                manager.load_config()
    
    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            manager = ConfigManager(config_dir)
            
            # Load default config
            config = manager.load_config()
            
            # Modify config
            config.project_name = "saved-project"
            config.cluster.nodes = 7
            
            # Save config
            save_path = config_dir / "saved-config.yaml"
            manager.save_config(config, save_path)
            
            # Verify saved config
            with open(save_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["project_name"] == "saved-project"
            assert saved_data["cluster"]["nodes"] == 7


class TestConfigModels:
    """Test configuration data models."""
    
    def test_gke_local_config_creation(self):
        """Test creating GKELocalConfig with valid data."""
        config_data = {
            "project_name": "test-project",
            "environment": "local"
        }
        
        config = GKELocalConfig(**config_data)
        
        assert config.project_name == "test-project"
        assert config.environment == "local"
        assert config.cluster.name == "local-gke-dev"  # Default value
    
    def test_project_name_validation(self):
        """Test project name validation."""
        # Valid names
        valid_names = ["test-project", "test_project", "testproject123"]
        for name in valid_names:
            config = GKELocalConfig(project_name=name)
            assert config.project_name == name.lower()
        
        # Invalid names
        invalid_names = ["test project", "test@project", ""]
        for name in invalid_names:
            with pytest.raises(ValueError):
                GKELocalConfig(project_name=name)
    
    def test_kubernetes_version_validation(self):
        """Test Kubernetes version validation."""
        # Valid versions
        valid_versions = ["1.28", "1.27", "1.29"]
        for version in valid_versions:
            config = GKELocalConfig(
                project_name="test",
                cluster={"kubernetes_version": version}
            )
            assert config.cluster.kubernetes_version == version
        
        # Invalid versions
        invalid_versions = ["1.28.0", "v1.28", "latest", "1"]
        for version in invalid_versions:
            with pytest.raises(ValueError):
                GKELocalConfig(
                    project_name="test",
                    cluster={"kubernetes_version": version}
                )
    
    def test_config_defaults(self):
        """Test that default values are properly set."""
        config = GKELocalConfig(project_name="test")
        
        # Check defaults
        assert config.log_level == LogLevel.INFO
        assert config.cluster.nodes == 3
        assert config.simulation.cloud_run.enabled is True
        assert config.services.monitoring.prometheus is True
        assert len(config.watch_paths) > 0
        assert len(config.ignore_patterns) > 0