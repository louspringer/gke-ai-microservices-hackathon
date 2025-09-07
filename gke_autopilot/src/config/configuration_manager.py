"""
Configuration Management System for GKE Autopilot Deployment Framework

This module provides comprehensive configuration management with schema validation,
environment variable overrides, templating, and multi-environment support.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
import logging
from jinja2 import Template, Environment, FileSystemLoader
import jsonschema
from jsonschema import validate, ValidationError

from ..models.app_config import AppConfig, ClusterConfig


logger = logging.getLogger(__name__)


@dataclass
class ConfigurationTemplate:
    """Configuration template with Jinja2 support"""
    name: str
    template_path: Path
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def render(self, context: Dict[str, Any]) -> str:
        """Render template with given context"""
        with open(self.template_path, 'r') as f:
            template_content = f.read()
        
        template = Template(template_content)
        merged_context = {**self.variables, **context}
        return template.render(**merged_context)


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""
    name: str
    app_config: AppConfig
    cluster_config: ClusterConfig
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'app_config': self.app_config.to_dict(),
            'cluster_config': self.cluster_config.to_dict(),
            'variables': self.variables
        }


class ConfigurationManager:
    """
    Comprehensive configuration management system for GKE Autopilot deployments.
    
    Features:
    - YAML/JSON configuration file parsing with schema validation
    - Environment variable override system
    - Configuration templating with Jinja2
    - Multi-environment configuration management
    - Configuration validation and error reporting
    """
    
    def __init__(self, config_dir: Union[str, Path] = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Template environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.config_dir / "templates")),
            autoescape=True
        )
        
        # Configuration schema
        self.app_config_schema = self._load_app_config_schema()
        self.cluster_config_schema = self._load_cluster_config_schema()
        
        # Environment configurations
        self.environments: Dict[str, EnvironmentConfig] = {}
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        
        logger.info(f"Initialized Configuration Manager with config directory: {self.config_dir}")
    
    def _load_app_config_schema(self) -> Dict[str, Any]:
        """Load JSON schema for application configuration validation"""
        return {
            "type": "object",
            "required": ["name", "image", "port"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$",
                    "maxLength": 63
                },
                "image": {
                    "type": "string",
                    "minLength": 1
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535
                },
                "environment_variables": {
                    "type": "object",
                    "patternProperties": {
                        "^[A-Z_][A-Z0-9_]*$": {"type": "string"}
                    }
                },
                "resources": {
                    "type": "object",
                    "properties": {
                        "cpu": {"type": "string", "pattern": "^[0-9]+m?$|^[0-9]*\\.?[0-9]+$"},
                        "memory": {"type": "string", "pattern": "^[0-9]+[KMGT]i?$"},
                        "storage": {"type": "string", "pattern": "^[0-9]+[KMGT]i?$"}
                    }
                },
                "scaling": {
                    "type": "object",
                    "properties": {
                        "min_replicas": {"type": "integer", "minimum": 1},
                        "max_replicas": {"type": "integer", "minimum": 1},
                        "target_cpu_utilization": {"type": "integer", "minimum": 1, "maximum": 100}
                    }
                },
                "healthChecks": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "pattern": "^/.*"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "initial_delay_seconds": {"type": "integer", "minimum": 0}
                    }
                },
                "ingress": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "domain": {"type": "string"},
                        "tls": {"type": "boolean"}
                    }
                }
            }
        }
    
    def _load_cluster_config_schema(self) -> Dict[str, Any]:
        """Load JSON schema for cluster configuration validation"""
        return {
            "type": "object",
            "required": ["name", "region"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$",
                    "maxLength": 40
                },
                "region": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$"
                },
                "network": {
                    "type": "object",
                    "properties": {
                        "vpc_name": {"type": "string"},
                        "subnet_name": {"type": "string"},
                        "enable_private_nodes": {"type": "boolean"},
                        "master_ipv4_cidr_block": {"type": "string"}
                    }
                },
                "security": {
                    "type": "object",
                    "properties": {
                        "enable_workload_identity": {"type": "boolean"},
                        "enable_network_policy": {"type": "boolean"},
                        "service_account": {"type": "string"}
                    }
                }
            }
        }
    
    def load_configuration(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from file with validation and caching.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
            
        Returns:
            Parsed and validated configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
            FileNotFoundError: If configuration file doesn't exist
        """
        config_path = Path(config_path)
        
        # Check cache first
        cache_key = str(config_path.absolute())
        if cache_key in self._config_cache:
            logger.debug(f"Returning cached configuration for {config_path}")
            return self._config_cache[cache_key]
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load configuration file
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
            
            logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
        
        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)
        
        # Validate configuration
        self._validate_configuration(config_data, config_path)
        
        # Cache configuration
        self._config_cache[cache_key] = config_data
        
        return config_data
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables follow the pattern: GKE_AUTOPILOT_<PATH>
        where PATH uses double underscores for nested keys.
        
        Examples:
        - GKE_AUTOPILOT_NAME -> config['name']
        - GKE_AUTOPILOT_RESOURCES__CPU -> config['resources']['cpu']
        - GKE_AUTOPILOT_SCALING__MIN_REPLICAS -> config['scaling']['min_replicas']
        """
        env_prefix = "GKE_AUTOPILOT_"
        
        for env_var, env_value in os.environ.items():
            if not env_var.startswith(env_prefix):
                continue
            
            # Parse environment variable path
            config_path = env_var[len(env_prefix):].lower()
            path_parts = config_path.split('__')
            
            # Navigate to the correct nested dictionary
            current_dict = config_data
            for part in path_parts[:-1]:
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]
            
            # Set the value (with type conversion)
            final_key = path_parts[-1]
            current_dict[final_key] = self._convert_env_value(env_value)
            
            logger.debug(f"Applied environment override: {env_var} -> {config_path}")
        
        return config_data
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _validate_configuration(self, config_data: Dict[str, Any], config_path: Path) -> None:
        """
        Validate configuration against JSON schema.
        
        Args:
            config_data: Configuration dictionary to validate
            config_path: Path to configuration file (for error reporting)
            
        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            # Determine configuration type and validate
            if 'name' in config_data and 'image' in config_data:
                # Application configuration
                validate(instance=config_data, schema=self.app_config_schema)
                logger.debug(f"Application configuration validation passed for {config_path}")
            elif 'name' in config_data and 'region' in config_data:
                # Cluster configuration
                validate(instance=config_data, schema=self.cluster_config_schema)
                logger.debug(f"Cluster configuration validation passed for {config_path}")
            else:
                logger.warning(f"Unknown configuration type for {config_path}")
                
        except ValidationError as e:
            error_msg = f"Configuration validation failed for {config_path}: {e.message}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
    
    def create_app_config(self, config_data: Dict[str, Any]) -> AppConfig:
        """
        Create AppConfig object from configuration dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            AppConfig object
        """
        return AppConfig.from_dict(config_data)
    
    def create_cluster_config(self, config_data: Dict[str, Any]) -> ClusterConfig:
        """
        Create ClusterConfig object from configuration dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            ClusterConfig object
        """
        # Extract nested configurations
        network_data = config_data.pop('network', {})
        security_data = config_data.pop('security', {})
        monitoring_data = config_data.pop('monitoring', {})
        
        from ..models.app_config import NetworkConfig, SecurityConfig, MonitoringConfig, CostOptimizationConfig
        
        network_config = NetworkConfig(**network_data) if network_data else NetworkConfig()
        security_config = SecurityConfig(**security_data) if security_data else SecurityConfig()
        monitoring_config = MonitoringConfig(**monitoring_data) if monitoring_data else MonitoringConfig()
        cost_config = CostOptimizationConfig()
        
        return ClusterConfig(
            network_config=network_config,
            security_config=security_config,
            monitoring_config=monitoring_config,
            cost_optimization=cost_config,
            **config_data
        )
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render configuration template with given context.
        
        Args:
            template_name: Name of template file
            context: Template context variables
            
        Returns:
            Rendered template content
        """
        try:
            template = self.jinja_env.get_template(template_name)
            rendered = template.render(**context)
            logger.debug(f"Rendered template {template_name}")
            return rendered
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise
    
    def create_environment_config(self, 
                                env_name: str, 
                                app_config_path: Union[str, Path],
                                cluster_config_path: Union[str, Path],
                                variables: Optional[Dict[str, Any]] = None) -> EnvironmentConfig:
        """
        Create environment-specific configuration.
        
        Args:
            env_name: Environment name (e.g., 'dev', 'staging', 'prod')
            app_config_path: Path to application configuration file
            cluster_config_path: Path to cluster configuration file
            variables: Additional environment variables
            
        Returns:
            EnvironmentConfig object
        """
        # Load configurations
        app_config_data = self.load_configuration(app_config_path)
        cluster_config_data = self.load_configuration(cluster_config_path)
        
        # Create configuration objects
        app_config = self.create_app_config(app_config_data)
        cluster_config = self.create_cluster_config(cluster_config_data)
        
        # Create environment configuration
        env_config = EnvironmentConfig(
            name=env_name,
            app_config=app_config,
            cluster_config=cluster_config,
            variables=variables or {}
        )
        
        # Cache environment configuration
        self.environments[env_name] = env_config
        
        logger.info(f"Created environment configuration for {env_name}")
        return env_config
    
    def get_environment_config(self, env_name: str) -> Optional[EnvironmentConfig]:
        """Get cached environment configuration"""
        return self.environments.get(env_name)
    
    def list_environments(self) -> List[str]:
        """List all configured environments"""
        return list(self.environments.keys())
    
    def save_configuration(self, config_data: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """
        Save configuration to file.
        
        Args:
            config_data: Configuration dictionary to save
            output_path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                if output_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif output_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported output format: {output_path.suffix}")
            
            logger.info(f"Saved configuration to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {output_path}: {e}")
            raise
    
    def merge_configurations(self, *config_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries with deep merging.
        
        Args:
            *config_dicts: Configuration dictionaries to merge
            
        Returns:
            Merged configuration dictionary
        """
        def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
            """Deep merge two dictionaries"""
            result = base.copy()
            
            for key, value in overlay.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            
            return result
        
        if not config_dicts:
            return {}
        
        result = config_dicts[0].copy()
        for config_dict in config_dicts[1:]:
            result = deep_merge(result, config_dict)
        
        return result
    
    def validate_gke_autopilot_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration for GKE Autopilot compatibility.
        
        Args:
            config_data: Configuration dictionary to validate
            
        Returns:
            Validation result with warnings and recommendations
        """
        result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Check resource requests
        resources = config_data.get('resources', {})
        
        # CPU validation
        cpu = resources.get('cpu', '100m')
        if cpu.endswith('m'):
            cpu_millicores = int(cpu[:-1])
            if cpu_millicores < 250:
                result['warnings'].append("CPU request < 250m may not be optimal for GKE Autopilot")
                result['recommendations'].append("Consider increasing CPU to 250m or higher")
        
        # Memory validation
        memory = resources.get('memory', '256Mi')
        if memory.endswith('Mi'):
            memory_mb = int(memory[:-2])
            if memory_mb < 512:
                result['warnings'].append("Memory request < 512Mi may not be optimal for GKE Autopilot")
                result['recommendations'].append("Consider increasing memory to 512Mi or higher")
        
        # Scaling validation
        scaling = config_data.get('scaling', {})
        min_replicas = scaling.get('min_replicas', 1)
        if min_replicas == 0:
            result['errors'].append("GKE Autopilot requires minimum replicas >= 1")
            result['valid'] = False
        
        # Ingress validation
        ingress = config_data.get('ingress', {})
        if ingress.get('enabled', False) and not ingress.get('tls', False):
            result['recommendations'].append("Enable TLS for production ingress")
        
        return result
    
    def create_sample_configs(self) -> None:
        """Create sample configuration files for reference"""
        sample_dir = self.config_dir / "samples"
        sample_dir.mkdir(exist_ok=True)
        
        # Sample application configuration
        app_config = {
            "name": "sample-app",
            "image": "gcr.io/google-samples/hello-app:1.0",
            "port": 8080,
            "environment_variables": {
                "ENV": "production",
                "LOG_LEVEL": "info"
            },
            "resources": {
                "cpu": "250m",
                "memory": "512Mi",
                "storage": "1Gi"
            },
            "scaling": {
                "min_replicas": 2,
                "max_replicas": 10,
                "target_cpu_utilization": 70
            },
            "healthChecks": {
                "path": "/health",
                "port": 8080,
                "initial_delay_seconds": 30
            },
            "ingress": {
                "enabled": True,
                "domain": "sample-app.example.com",
                "tls": True
            }
        }
        
        # Sample cluster configuration
        cluster_config = {
            "name": "sample-cluster",
            "region": "us-central1",
            "network": {
                "enable_private_nodes": True,
                "master_ipv4_cidr_block": "172.16.0.0/28"
            },
            "security": {
                "enable_workload_identity": True,
                "enable_network_policy": True
            },
            "monitoring": {
                "enable_logging": True,
                "enable_monitoring": True,
                "log_retention_days": 30
            }
        }
        
        # Save sample configurations
        self.save_configuration(app_config, sample_dir / "app-config.yaml")
        self.save_configuration(cluster_config, sample_dir / "cluster-config.yaml")
        
        logger.info(f"Created sample configurations in {sample_dir}")
    
    def clear_cache(self) -> None:
        """Clear configuration cache"""
        self._config_cache.clear()
        logger.info("Configuration cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get configuration cache statistics"""
        return {
            'cached_configs': len(self._config_cache),
            'cached_environments': len(self.environments),
            'cache_keys': list(self._config_cache.keys())
        }