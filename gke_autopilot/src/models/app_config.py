"""
Core Data Models for GKE Autopilot Deployment Framework

This module provides comprehensive data models for application configuration,
cluster management, and deployment results with full validation and serialization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import yaml
import json
from pathlib import Path


class DeploymentPhase(Enum):
    """Deployment phases for tracking progress"""
    PENDING = "pending"
    CREATING_CLUSTER = "creating_cluster"
    DEPLOYING_APP = "deploying_app"
    CONFIGURING_INGRESS = "configuring_ingress"
    READY = "ready"
    FAILED = "failed"
    UPDATING = "updating"
    DELETING = "deleting"


class ScalingMode(Enum):
    """Scaling modes for application deployment"""
    MANUAL = "manual"
    AUTO_CPU = "auto_cpu"
    AUTO_MEMORY = "auto_memory"
    AUTO_CUSTOM = "auto_custom"


@dataclass
class ResourceRequests:
    """Resource requests and limits for containers"""
    cpu: str = "100m"
    memory: str = "256Mi"
    storage: str = "1Gi"
    
    def __post_init__(self):
        """Validate resource specifications"""
        if not self.cpu or not self.memory:
            raise ValueError("CPU and memory requests are required")
        
        # Validate CPU format (e.g., "100m", "0.1", "1")
        if not (self.cpu.endswith('m') or self.cpu.replace('.', '').isdigit()):
            raise ValueError(f"Invalid CPU format: {self.cpu}")
        
        # Validate memory format (e.g., "256Mi", "1Gi", "512M")
        if not any(self.memory.endswith(suffix) for suffix in ['Mi', 'Gi', 'M', 'G', 'Ki', 'K']):
            raise ValueError(f"Invalid memory format: {self.memory}")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for Kubernetes manifests"""
        return {
            "cpu": self.cpu,
            "memory": self.memory,
            "ephemeral-storage": self.storage
        }


@dataclass
class HealthCheckConfig:
    """Health check configuration for readiness and liveness probes"""
    path: str = "/health"
    port: int = 8080
    initial_delay_seconds: int = 30
    period_seconds: int = 10
    timeout_seconds: int = 5
    failure_threshold: int = 3
    success_threshold: int = 1
    
    def __post_init__(self):
        """Validate health check configuration"""
        if not self.path.startswith('/'):
            raise ValueError("Health check path must start with '/'")
        
        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        
        if self.initial_delay_seconds < 0:
            raise ValueError("Initial delay must be non-negative")
    
    def to_kubernetes_probe(self) -> Dict[str, Any]:
        """Convert to Kubernetes probe configuration"""
        return {
            "httpGet": {
                "path": self.path,
                "port": self.port
            },
            "initialDelaySeconds": self.initial_delay_seconds,
            "periodSeconds": self.period_seconds,
            "timeoutSeconds": self.timeout_seconds,
            "failureThreshold": self.failure_threshold,
            "successThreshold": self.success_threshold
        }


@dataclass
class ScalingConfig:
    """Horizontal Pod Autoscaler configuration"""
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: int = 70
    target_memory_utilization: int = 80
    scale_up_stabilization: int = 60
    scale_down_stabilization: int = 300
    mode: ScalingMode = ScalingMode.AUTO_CPU
    
    def __post_init__(self):
        """Validate scaling configuration"""
        if self.min_replicas < 1:
            raise ValueError("Minimum replicas must be at least 1")
        
        if self.max_replicas < self.min_replicas:
            raise ValueError("Maximum replicas must be >= minimum replicas")
        
        if not (1 <= self.target_cpu_utilization <= 100):
            raise ValueError("CPU utilization must be between 1 and 100")
        
        if not (1 <= self.target_memory_utilization <= 100):
            raise ValueError("Memory utilization must be between 1 and 100")
    
    def to_hpa_spec(self) -> Dict[str, Any]:
        """Convert to Kubernetes HPA specification"""
        spec = {
            "minReplicas": self.min_replicas,
            "maxReplicas": self.max_replicas,
            "behavior": {
                "scaleUp": {
                    "stabilizationWindowSeconds": self.scale_up_stabilization
                },
                "scaleDown": {
                    "stabilizationWindowSeconds": self.scale_down_stabilization
                }
            }
        }
        
        if self.mode == ScalingMode.AUTO_CPU:
            spec["targetCPUUtilizationPercentage"] = self.target_cpu_utilization
        elif self.mode == ScalingMode.AUTO_MEMORY:
            spec["metrics"] = [{
                "type": "Resource",
                "resource": {
                    "name": "memory",
                    "target": {
                        "type": "Utilization",
                        "averageUtilization": self.target_memory_utilization
                    }
                }
            }]
        
        return spec


@dataclass
class IngressConfig:
    """Ingress configuration for external access"""
    enabled: bool = True
    domain: Optional[str] = None
    tls: bool = True
    annotations: Dict[str, str] = field(default_factory=dict)
    path: str = "/"
    path_type: str = "Prefix"
    
    def __post_init__(self):
        """Validate ingress configuration"""
        if self.enabled and not self.domain:
            raise ValueError("Domain is required when ingress is enabled")
        
        if self.domain and not self.domain.replace('-', '').replace('.', '').isalnum():
            raise ValueError("Invalid domain format")
        
        if not self.path.startswith('/'):
            raise ValueError("Ingress path must start with '/'")
    
    def to_kubernetes_ingress(self, service_name: str, service_port: int) -> Dict[str, Any]:
        """Convert to Kubernetes Ingress specification"""
        if not self.enabled:
            return {}
        
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{service_name}-ingress",
                "annotations": {
                    "kubernetes.io/ingress.class": "gce",
                    "kubernetes.io/ingress.global-static-ip-name": f"{service_name}-ip",
                    **self.annotations
                }
            },
            "spec": {
                "rules": [{
                    "host": self.domain,
                    "http": {
                        "paths": [{
                            "path": self.path,
                            "pathType": self.path_type,
                            "backend": {
                                "service": {
                                    "name": service_name,
                                    "port": {"number": service_port}
                                }
                            }
                        }]
                    }
                }]
            }
        }
        
        if self.tls and self.domain:
            ingress["spec"]["tls"] = [{
                "hosts": [self.domain],
                "secretName": f"{service_name}-tls"
            }]
            
            # Add managed certificate annotation
            ingress["metadata"]["annotations"]["networking.gke.io/managed-certificates"] = f"{service_name}-cert"
        
        return ingress


@dataclass
class AppConfig:
    """Complete application configuration for GKE Autopilot deployment"""
    name: str
    image: str
    port: int = 8080
    environment_variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    resource_requests: ResourceRequests = field(default_factory=ResourceRequests)
    scaling_config: ScalingConfig = field(default_factory=ScalingConfig)
    health_checks: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    ingress_config: IngressConfig = field(default_factory=IngressConfig)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate application configuration"""
        if not self.name:
            raise ValueError("Application name is required")
        
        if not self.name.replace('-', '').isalnum():
            raise ValueError("Application name must be alphanumeric with hyphens")
        
        if len(self.name) > 63:
            raise ValueError("Application name must be 63 characters or less")
        
        if not self.image:
            raise ValueError("Container image is required")
        
        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        
        # Validate environment variable names
        for env_name in self.environment_variables.keys():
            if not env_name.replace('_', '').isalnum():
                raise ValueError(f"Invalid environment variable name: {env_name}")
    
    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> 'AppConfig':
        """Load configuration from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create AppConfig from dictionary"""
        # Extract nested configurations
        resource_data = data.pop('resources', {})
        scaling_data = data.pop('scaling', {})
        health_data = data.pop('healthChecks', {})
        ingress_data = data.pop('ingress', {})
        
        # Create nested objects
        resources = ResourceRequests(**resource_data) if resource_data else ResourceRequests()
        scaling = ScalingConfig(**scaling_data) if scaling_data else ScalingConfig()
        health = HealthCheckConfig(**health_data) if health_data else HealthCheckConfig()
        ingress = IngressConfig(**ingress_data) if ingress_data else IngressConfig()
        
        return cls(
            resource_requests=resources,
            scaling_config=scaling,
            health_checks=health,
            ingress_config=ingress,
            **data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'image': self.image,
            'port': self.port,
            'environment_variables': self.environment_variables,
            'secrets': self.secrets,
            'resources': {
                'cpu': self.resource_requests.cpu,
                'memory': self.resource_requests.memory,
                'storage': self.resource_requests.storage
            },
            'scaling': {
                'min_replicas': self.scaling_config.min_replicas,
                'max_replicas': self.scaling_config.max_replicas,
                'target_cpu_utilization': self.scaling_config.target_cpu_utilization,
                'mode': self.scaling_config.mode.value
            },
            'healthChecks': {
                'path': self.health_checks.path,
                'port': self.health_checks.port,
                'initial_delay_seconds': self.health_checks.initial_delay_seconds
            },
            'ingress': {
                'enabled': self.ingress_config.enabled,
                'domain': self.ingress_config.domain,
                'tls': self.ingress_config.tls
            },
            'labels': self.labels,
            'annotations': self.annotations
        }
    
    def to_yaml(self, yaml_path: Union[str, Path]) -> None:
        """Save configuration to YAML file"""
        with open(yaml_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    def validate_for_gke_autopilot(self) -> List[str]:
        """Validate configuration for GKE Autopilot compatibility"""
        warnings = []
        
        # Check resource requests for Autopilot optimization
        cpu_val = self.resource_requests.cpu
        if cpu_val.endswith('m'):
            cpu_millicores = int(cpu_val[:-1])
            if cpu_millicores < 250:
                warnings.append("CPU request < 250m may not be optimal for GKE Autopilot")
        
        # Check memory requests
        memory_val = self.resource_requests.memory
        if memory_val.endswith('Mi'):
            memory_mb = int(memory_val[:-2])
            if memory_mb < 512:
                warnings.append("Memory request < 512Mi may not be optimal for GKE Autopilot")
        
        # Check scaling configuration
        if self.scaling_config.min_replicas == 0:
            warnings.append("Minimum replicas of 0 not supported in GKE Autopilot")
        
        return warnings


@dataclass
class NetworkConfig:
    """Network configuration for GKE cluster"""
    vpc_name: Optional[str] = None
    subnet_name: Optional[str] = None
    enable_private_nodes: bool = True
    enable_private_endpoint: bool = False
    master_ipv4_cidr_block: str = "172.16.0.0/28"
    pod_cidr: str = "10.244.0.0/14"
    service_cidr: str = "10.0.0.0/20"
    
    def __post_init__(self):
        """Validate network configuration"""
        import ipaddress
        
        try:
            ipaddress.IPv4Network(self.master_ipv4_cidr_block)
            ipaddress.IPv4Network(self.pod_cidr)
            ipaddress.IPv4Network(self.service_cidr)
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid CIDR block: {e}")


@dataclass
class SecurityConfig:
    """Security configuration for GKE cluster"""
    enable_workload_identity: bool = True
    enable_network_policy: bool = True
    enable_pod_security_policy: bool = True
    enable_shielded_nodes: bool = True
    service_account: Optional[str] = None
    
    def __post_init__(self):
        """Validate security configuration"""
        if self.service_account and '@' not in self.service_account:
            raise ValueError("Service account must be in email format")


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    enable_logging: bool = True
    enable_monitoring: bool = True
    enable_managed_prometheus: bool = True
    log_retention_days: int = 30
    
    def __post_init__(self):
        """Validate monitoring configuration"""
        if self.log_retention_days < 1:
            raise ValueError("Log retention must be at least 1 day")


@dataclass
class CostOptimizationConfig:
    """Cost optimization settings"""
    enable_autopilot: bool = True
    enable_spot_instances: bool = False
    enable_preemptible_nodes: bool = False
    
    def __post_init__(self):
        """Validate cost optimization settings"""
        if self.enable_spot_instances and self.enable_preemptible_nodes:
            raise ValueError("Cannot enable both spot instances and preemptible nodes")


@dataclass
class ClusterConfig:
    """Complete cluster configuration for GKE Autopilot"""
    name: str
    region: str = "us-central1"
    network_config: NetworkConfig = field(default_factory=NetworkConfig)
    security_config: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring_config: MonitoringConfig = field(default_factory=MonitoringConfig)
    cost_optimization: CostOptimizationConfig = field(default_factory=CostOptimizationConfig)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate cluster configuration"""
        if not self.name:
            raise ValueError("Cluster name is required")
        
        if not self.name.replace('-', '').isalnum():
            raise ValueError("Cluster name must be alphanumeric with hyphens")
        
        if len(self.name) > 40:
            raise ValueError("Cluster name must be 40 characters or less")
        
        if not self.region:
            raise ValueError("Region is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'region': self.region,
            'network': {
                'vpc_name': self.network_config.vpc_name,
                'subnet_name': self.network_config.subnet_name,
                'enable_private_nodes': self.network_config.enable_private_nodes,
                'master_ipv4_cidr_block': self.network_config.master_ipv4_cidr_block
            },
            'security': {
                'enable_workload_identity': self.security_config.enable_workload_identity,
                'enable_network_policy': self.security_config.enable_network_policy,
                'service_account': self.security_config.service_account
            },
            'monitoring': {
                'enable_logging': self.monitoring_config.enable_logging,
                'enable_monitoring': self.monitoring_config.enable_monitoring,
                'log_retention_days': self.monitoring_config.log_retention_days
            },
            'labels': self.labels
        }


@dataclass
class ResourceUsage:
    """Resource usage metrics"""
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    storage_gb: float = 0.0
    network_gb: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'cpu_cores': self.cpu_cores,
            'memory_gb': self.memory_gb,
            'storage_gb': self.storage_gb,
            'network_gb': self.network_gb
        }


@dataclass
class CostEstimate:
    """Cost estimation for deployment"""
    hourly_cost: float = 0.0
    daily_cost: float = 0.0
    monthly_cost: float = 0.0
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived costs"""
        if self.hourly_cost > 0:
            self.daily_cost = self.hourly_cost * 24
            self.monthly_cost = self.daily_cost * 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'hourly_cost': self.hourly_cost,
            'daily_cost': self.daily_cost,
            'monthly_cost': self.monthly_cost,
            'cost_breakdown': self.cost_breakdown
        }


@dataclass
class DeploymentResult:
    """Result of a deployment operation"""
    success: bool
    cluster_name: str
    application_url: Optional[str] = None
    deployment_time: datetime = field(default_factory=datetime.utcnow)
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)
    cost_estimate: CostEstimate = field(default_factory=CostEstimate)
    monitoring_dashboard: Optional[str] = None
    phase: DeploymentPhase = DeploymentPhase.PENDING
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'success': self.success,
            'cluster_name': self.cluster_name,
            'application_url': self.application_url,
            'deployment_time': self.deployment_time.isoformat(),
            'resource_usage': self.resource_usage.to_dict(),
            'cost_estimate': self.cost_estimate.to_dict(),
            'monitoring_dashboard': self.monitoring_dashboard,
            'phase': self.phase.value,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentResult':
        """Create from dictionary"""
        resource_data = data.pop('resource_usage', {})
        cost_data = data.pop('cost_estimate', {})
        
        return cls(
            resource_usage=ResourceUsage(**resource_data),
            cost_estimate=CostEstimate(**cost_data),
            deployment_time=datetime.fromisoformat(data.pop('deployment_time')),
            phase=DeploymentPhase(data.pop('phase', 'pending')),
            **data
        )


# Utility functions for configuration management

def load_app_config(config_path: Union[str, Path]) -> AppConfig:
    """Load application configuration from file"""
    config_path = Path(config_path)
    
    if config_path.suffix.lower() in ['.yaml', '.yml']:
        return AppConfig.from_yaml(config_path)
    elif config_path.suffix.lower() == '.json':
        with open(config_path, 'r') as f:
            data = json.load(f)
        return AppConfig.from_dict(data)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")


def create_sample_config() -> AppConfig:
    """Create a sample application configuration"""
    return AppConfig(
        name="sample-app",
        image="gcr.io/google-samples/hello-app:1.0",
        port=8080,
        environment_variables={
            "ENV": "production",
            "LOG_LEVEL": "info"
        },
        resource_requests=ResourceRequests(
            cpu="250m",
            memory="512Mi"
        ),
        scaling_config=ScalingConfig(
            min_replicas=2,
            max_replicas=10,
            target_cpu_utilization=70
        ),
        health_checks=HealthCheckConfig(
            path="/health",
            port=8080
        ),
        ingress_config=IngressConfig(
            enabled=True,
            domain="sample-app.example.com",
            tls=True
        )
    )


def validate_gke_autopilot_compatibility(config: AppConfig) -> Dict[str, Any]:
    """Comprehensive GKE Autopilot compatibility validation"""
    result = {
        'compatible': True,
        'warnings': [],
        'errors': [],
        'recommendations': []
    }
    
    # Check resource requests
    warnings = config.validate_for_gke_autopilot()
    result['warnings'].extend(warnings)
    
    # Check for Autopilot-specific requirements
    if config.scaling_config.min_replicas == 0:
        result['errors'].append("GKE Autopilot requires minimum replicas >= 1")
        result['compatible'] = False
    
    # Add recommendations
    if config.resource_requests.cpu == "100m":
        result['recommendations'].append("Consider increasing CPU to 250m for better Autopilot performance")
    
    if not config.ingress_config.tls:
        result['recommendations'].append("Enable TLS for production deployments")
    
    return result