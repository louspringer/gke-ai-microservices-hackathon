"""Configuration data models using Pydantic for validation."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CloudRunConfig(BaseModel):
    """Configuration for Cloud Run simulation."""
    enabled: bool = True
    scale_to_zero: bool = True
    cold_start_delay: str = "2s"
    max_instances: int = 100
    concurrency: int = 80
    timeout: str = "300s"


class AutopilotConfig(BaseModel):
    """Configuration for GKE Autopilot simulation."""
    enabled: bool = True
    node_auto_provisioning: bool = True
    resource_optimization: bool = True
    security_policies: bool = True
    intelligent_scheduling: bool = True


class SimulationConfig(BaseModel):
    """Simulation layer configuration."""
    cloud_run: CloudRunConfig = CloudRunConfig()
    autopilot: AutopilotConfig = AutopilotConfig()


class ClusterConfig(BaseModel):
    """Local Kubernetes cluster configuration."""
    name: str = "local-gke-dev"
    kubernetes_version: str = "1.28"
    nodes: int = 3
    registry_port: int = 5000
    ingress_port: int = 80
    api_server_port: int = 6443
    
    @field_validator('kubernetes_version')
    @classmethod
    def validate_k8s_version(cls, v):
        # Basic version format validation
        parts = v.split('.')
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError('Kubernetes version must be in format "X.Y"')
        return v


class MonitoringConfig(BaseModel):
    """Monitoring stack configuration."""
    prometheus: bool = True
    grafana: bool = True
    jaeger: bool = True
    prometheus_port: int = 9090
    grafana_port: int = 3000
    jaeger_port: int = 16686


class AIConfig(BaseModel):
    """AI services configuration."""
    model_serving: bool = True
    ghostbusters: bool = True
    gpu_support: bool = False
    inference_timeout: int = 30


class ServicesConfig(BaseModel):
    """Development services configuration."""
    monitoring: MonitoringConfig = MonitoringConfig()
    ai: AIConfig = AIConfig()
    hot_reload: bool = True
    debug_proxy: bool = True
    log_aggregation: bool = True


class GKELocalConfig(BaseModel):
    """Main configuration model for GKE Local."""
    
    # Core settings
    project_name: str = Field(..., description="Project name")
    environment: str = Field(default="local", description="Environment name")
    log_level: LogLevel = LogLevel.INFO
    
    # Component configurations
    cluster: ClusterConfig = ClusterConfig()
    simulation: SimulationConfig = SimulationConfig()
    services: ServicesConfig = ServicesConfig()
    
    # Environment variables and secrets
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    secrets: Dict[str, str] = Field(default_factory=dict)
    
    # Development settings
    watch_paths: List[str] = Field(default_factory=lambda: ["./src", "./services"])
    ignore_patterns: List[str] = Field(default_factory=lambda: [
        "*.pyc", "__pycache__", ".git", "node_modules", ".venv"
    ])
    
    @field_validator('project_name')
    @classmethod
    def validate_project_name(cls, v):
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Project name must be alphanumeric with hyphens or underscores')
        return v.lower()
    
    model_config = ConfigDict(
        use_enum_values=True,
        extra="forbid"  # Prevent extra fields
    )