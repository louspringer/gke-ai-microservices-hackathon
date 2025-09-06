"""Configuration manager for loading and managing YAML configurations."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from .models import GKELocalConfig


class ConfigManager:
    """Manages configuration loading, validation, and environment-specific overrides."""
    
    DEFAULT_CONFIG_NAME = "gke-local.yaml"
    ENV_CONFIG_PATTERN = "gke-local.{env}.yaml"
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory to search for config files. Defaults to current directory.
        """
        self.config_dir = config_dir or Path.cwd()
        self._config: Optional[GKELocalConfig] = None
        self._config_files_loaded: List[Path] = []
    
    def load_config(self, environment: str = "local") -> GKELocalConfig:
        """Load configuration with environment-specific overrides.
        
        Args:
            environment: Environment name for loading environment-specific config
            
        Returns:
            Validated GKELocalConfig instance
            
        Raises:
            FileNotFoundError: If no configuration files are found
            ValueError: If configuration validation fails
        """
        # Load base configuration
        base_config = self._load_base_config()
        
        # Load environment-specific overrides
        env_overrides = self._load_env_config(environment)
        
        # Merge configurations
        merged_config = self._merge_configs(base_config, env_overrides)
        
        # Set environment in config
        merged_config["environment"] = environment
        
        # Validate and create config object
        try:
            self._config = GKELocalConfig(**merged_config)
            return self._config
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration from default config file."""
        config_path = self.config_dir / self.DEFAULT_CONFIG_NAME
        
        if not config_path.exists():
            # Create default configuration if none exists
            self._create_default_config(config_path)
        
        return self._load_yaml_file(config_path)
    
    def _load_env_config(self, environment: str) -> Dict[str, Any]:
        """Load environment-specific configuration overrides."""
        env_config_name = self.ENV_CONFIG_PATTERN.format(env=environment)
        env_config_path = self.config_dir / env_config_name
        
        if env_config_path.exists():
            return self._load_yaml_file(env_config_path)
        
        return {}
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f) or {}
                self._config_files_loaded.append(file_path)
                return content
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise FileNotFoundError(f"Could not read config file {file_path}: {e}")
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_default_config(self, config_path: Path) -> None:
        """Create a default configuration file."""
        default_config = {
            "project_name": "my-gke-local-project",
            "environment": "local",
            "log_level": "info",
            
            "cluster": {
                "name": "local-gke-dev",
                "kubernetes_version": "1.28",
                "nodes": 3
            },
            
            "simulation": {
                "cloud_run": {
                    "enabled": True,
                    "scale_to_zero": True,
                    "cold_start_delay": "2s"
                },
                "autopilot": {
                    "enabled": True,
                    "node_auto_provisioning": True,
                    "resource_optimization": True
                }
            },
            
            "services": {
                "monitoring": {
                    "prometheus": True,
                    "grafana": True,
                    "jaeger": True
                },
                "ai": {
                    "model_serving": True,
                    "ghostbusters": True,
                    "gpu_support": False
                }
            },
            
            "watch_paths": ["./src", "./services"],
            "ignore_patterns": ["*.pyc", "__pycache__", ".git", "node_modules", ".venv"]
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    def get_config(self) -> Optional[GKELocalConfig]:
        """Get the currently loaded configuration."""
        return self._config
    
    def get_loaded_files(self) -> List[Path]:
        """Get list of configuration files that were loaded."""
        return self._config_files_loaded.copy()
    
    def save_config(self, config: GKELocalConfig, file_path: Optional[Path] = None) -> None:
        """Save configuration to YAML file.
        
        Args:
            config: Configuration to save
            file_path: Path to save to. Defaults to default config file.
        """
        if file_path is None:
            file_path = self.config_dir / self.DEFAULT_CONFIG_NAME
        
        # Convert config to dict, excluding None values
        config_dict = config.model_dump(exclude_none=True)
        
        with open(file_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)