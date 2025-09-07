"""
Validation Engine for GKE Autopilot Deployment Framework

This module provides comprehensive validation for application configurations,
container images, and GKE Autopilot compatibility with detailed feedback.
"""

import logging
import re
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
from pathlib import Path

from ..models.app_config import AppConfig, ClusterConfig, ResourceRequests, ScalingConfig


logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    RECOMMENDATION = "recommendation"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    level: ValidationLevel
    category: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level.value,
            'category': self.category,
            'message': self.message,
            'field': self.field,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    valid: bool = True
    results: List[ValidationResult] = field(default_factory=list)
    
    def add_result(self, result: ValidationResult) -> None:
        """Add validation result"""
        self.results.append(result)
        if result.level == ValidationLevel.ERROR:
            self.valid = False
    
    def get_errors(self) -> List[ValidationResult]:
        """Get all error-level results"""
        return [r for r in self.results if r.level == ValidationLevel.ERROR]
    
    def get_warnings(self) -> List[ValidationResult]:
        """Get all warning-level results"""
        return [r for r in self.results if r.level == ValidationLevel.WARNING]
    
    def get_recommendations(self) -> List[ValidationResult]:
        """Get all recommendation-level results"""
        return [r for r in self.results if r.level == ValidationLevel.RECOMMENDATION]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'summary': {
                'errors': len(self.get_errors()),
                'warnings': len(self.get_warnings()),
                'recommendations': len(self.get_recommendations()),
                'total_issues': len(self.results)
            },
            'results': [r.to_dict() for r in self.results]
        }


class ValidationEngine:
    """
    Comprehensive validation engine for GKE Autopilot deployments.
    
    Features:
    - Application configuration validation with detailed feedback
    - Container image validation and security scanning integration
    - GKE Autopilot compatibility checks and recommendations
    - Resource optimization suggestions
    - Security best practices validation
    """
    
    def __init__(self):
        """Initialize validation engine"""
        self.session = None
        
        # Validation rules
        self.naming_pattern = re.compile(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$')
        self.domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
        self.image_pattern = re.compile(r'^([a-zA-Z0-9._-]+/)?[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+$|^([a-zA-Z0-9._-]+/)?[a-zA-Z0-9._-]+@sha256:[a-f0-9]{64}$')
        
        # GKE Autopilot resource limits
        self.autopilot_limits = {
            'cpu': {
                'min_millicores': 250,
                'max_millicores': 110000,  # 110 vCPUs
                'recommended_min': 250
            },
            'memory': {
                'min_mb': 512,
                'max_gb': 420,  # 420 GB
                'recommended_min_mb': 512
            },
            'storage': {
                'min_gb': 1,
                'max_gb': 64000,  # 64 TB
                'recommended_min_gb': 1
            }
        }
        
        logger.info("Validation engine initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def validate_app_config(self, app_config: AppConfig) -> ValidationReport:
        """
        Comprehensive validation of application configuration.
        
        Args:
            app_config: Application configuration to validate
            
        Returns:
            ValidationReport: Detailed validation results
        """
        logger.info(f"Validating application configuration: {app_config.name}")
        
        report = ValidationReport()
        
        # Basic configuration validation
        self._validate_basic_config(app_config, report)
        
        # Resource validation
        self._validate_resources(app_config.resource_requests, report)
        
        # Scaling configuration validation
        self._validate_scaling_config(app_config.scaling_config, report)
        
        # Health check validation
        self._validate_health_checks(app_config.health_checks, report)
        
        # Ingress configuration validation
        self._validate_ingress_config(app_config.ingress_config, report)
        
        # GKE Autopilot specific validation
        self._validate_autopilot_compatibility(app_config, report)
        
        # Security validation
        self._validate_security_config(app_config, report)
        
        # Container image validation (async)
        if self.session:
            await self._validate_container_image(app_config.image, report)
        
        logger.info(f"Validation completed for {app_config.name}: {len(report.results)} issues found")
        return report
    
    def _validate_basic_config(self, app_config: AppConfig, report: ValidationReport) -> None:
        """Validate basic application configuration"""
        
        # Application name validation
        if not app_config.name:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="configuration",
                message="Application name is required",
                field="name"
            ))
        elif not self.naming_pattern.match(app_config.name):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="configuration",
                message="Application name must be lowercase alphanumeric with hyphens",
                field="name",
                suggestion="Use only lowercase letters, numbers, and hyphens"
            ))
        elif len(app_config.name) > 63:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="configuration",
                message="Application name must be 63 characters or less",
                field="name"
            ))
        
        # Container image validation
        if not app_config.image:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="configuration",
                message="Container image is required",
                field="image"
            ))
        elif not self.image_pattern.match(app_config.image):
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="configuration",
                message="Container image format may be invalid",
                field="image",
                suggestion="Use format: registry/image:tag or registry/image@sha256:digest"
            ))
        
        # Port validation
        if not (1 <= app_config.port <= 65535):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="configuration",
                message="Port must be between 1 and 65535",
                field="port"
            ))
        elif app_config.port < 1024:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="security",
                message="Using privileged port (< 1024) may require special permissions",
                field="port",
                suggestion="Consider using port >= 1024 for better security"
            ))
        
        # Environment variables validation
        for env_name, env_value in app_config.environment_variables.items():
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', env_name):
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="configuration",
                    message=f"Environment variable name '{env_name}' should be uppercase with underscores",
                    field="environment_variables",
                    suggestion="Use UPPER_CASE format for environment variable names"
                ))
    
    def _validate_resources(self, resources: ResourceRequests, report: ValidationReport) -> None:
        """Validate resource requests and limits"""
        
        # CPU validation
        cpu_millicores = self._parse_cpu_to_millicores(resources.cpu)
        if cpu_millicores is None:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="resources",
                message=f"Invalid CPU format: {resources.cpu}",
                field="resources.cpu",
                suggestion="Use format like '250m', '0.5', or '1'"
            ))
        else:
            if cpu_millicores < self.autopilot_limits['cpu']['min_millicores']:
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="resources",
                    message=f"CPU request {resources.cpu} is below GKE Autopilot minimum (250m)",
                    field="resources.cpu",
                    suggestion="Increase CPU to at least 250m for optimal Autopilot performance"
                ))
            elif cpu_millicores > self.autopilot_limits['cpu']['max_millicores']:
                report.add_result(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="resources",
                    message=f"CPU request {resources.cpu} exceeds GKE Autopilot maximum (110 vCPUs)",
                    field="resources.cpu"
                ))
        
        # Memory validation
        memory_mb = self._parse_memory_to_mb(resources.memory)
        if memory_mb is None:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="resources",
                message=f"Invalid memory format: {resources.memory}",
                field="resources.memory",
                suggestion="Use format like '512Mi', '1Gi', or '2G'"
            ))
        else:
            if memory_mb < self.autopilot_limits['memory']['min_mb']:
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="resources",
                    message=f"Memory request {resources.memory} is below GKE Autopilot minimum (512Mi)",
                    field="resources.memory",
                    suggestion="Increase memory to at least 512Mi for optimal Autopilot performance"
                ))
            elif memory_mb > self.autopilot_limits['memory']['max_gb'] * 1024:
                report.add_result(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="resources",
                    message=f"Memory request {resources.memory} exceeds GKE Autopilot maximum (420GB)",
                    field="resources.memory"
                ))
        
        # Storage validation
        storage_gb = self._parse_storage_to_gb(resources.storage)
        if storage_gb is None:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="resources",
                message=f"Invalid storage format: {resources.storage}",
                field="resources.storage",
                suggestion="Use format like '1Gi', '10G', or '100Gi'"
            ))
        elif storage_gb > self.autopilot_limits['storage']['max_gb']:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="resources",
                message=f"Storage request {resources.storage} exceeds GKE Autopilot maximum (64TB)",
                field="resources.storage"
            ))
        
        # Resource ratio validation
        if cpu_millicores and memory_mb:
            cpu_cores = cpu_millicores / 1000
            memory_gb = memory_mb / 1024
            
            # Check CPU to memory ratio (GKE Autopilot guidelines)
            if memory_gb / cpu_cores > 6.5:
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="resources",
                    message="Memory to CPU ratio is high, may not be cost-optimal",
                    field="resources",
                    suggestion="Consider adjusting CPU/memory ratio for better cost efficiency"
                ))
            elif memory_gb / cpu_cores < 0.5:
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="resources",
                    message="Memory to CPU ratio is low, may cause memory pressure",
                    field="resources",
                    suggestion="Consider increasing memory or decreasing CPU"
                ))
    
    def _validate_scaling_config(self, scaling: ScalingConfig, report: ValidationReport) -> None:
        """Validate scaling configuration"""
        
        if scaling.min_replicas < 1:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="scaling",
                message="Minimum replicas must be at least 1 for GKE Autopilot",
                field="scaling.min_replicas"
            ))
        
        if scaling.max_replicas < scaling.min_replicas:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="scaling",
                message="Maximum replicas must be greater than or equal to minimum replicas",
                field="scaling.max_replicas"
            ))
        
        if scaling.max_replicas > 1000:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="scaling",
                message="Very high maximum replicas may cause resource constraints",
                field="scaling.max_replicas",
                suggestion="Consider if you really need more than 1000 replicas"
            ))
        
        if not (1 <= scaling.target_cpu_utilization <= 100):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="scaling",
                message="Target CPU utilization must be between 1 and 100",
                field="scaling.target_cpu_utilization"
            ))
        elif scaling.target_cpu_utilization > 90:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="scaling",
                message="High CPU target may cause frequent scaling events",
                field="scaling.target_cpu_utilization",
                suggestion="Consider using 70-80% for more stable scaling"
            ))
        
        if not (1 <= scaling.target_memory_utilization <= 100):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="scaling",
                message="Target memory utilization must be between 1 and 100",
                field="scaling.target_memory_utilization"
            ))
    
    def _validate_health_checks(self, health_checks, report: ValidationReport) -> None:
        """Validate health check configuration"""
        
        if not health_checks.path.startswith('/'):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="health_checks",
                message="Health check path must start with '/'",
                field="health_checks.path"
            ))
        
        if not (1 <= health_checks.port <= 65535):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="health_checks",
                message="Health check port must be between 1 and 65535",
                field="health_checks.port"
            ))
        
        if health_checks.initial_delay_seconds < 0:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="health_checks",
                message="Initial delay must be non-negative",
                field="health_checks.initial_delay_seconds"
            ))
        elif health_checks.initial_delay_seconds < 10:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="health_checks",
                message="Very short initial delay may cause premature health check failures",
                field="health_checks.initial_delay_seconds",
                suggestion="Consider using at least 10 seconds initial delay"
            ))
        
        if health_checks.period_seconds < 1:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="health_checks",
                message="Period must be at least 1 second",
                field="health_checks.period_seconds"
            ))
        
        if health_checks.timeout_seconds >= health_checks.period_seconds:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="health_checks",
                message="Timeout should be less than period to avoid overlapping checks",
                field="health_checks.timeout_seconds"
            ))
    
    def _validate_ingress_config(self, ingress, report: ValidationReport) -> None:
        """Validate ingress configuration"""
        
        if ingress.enabled:
            if not ingress.domain:
                report.add_result(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="ingress",
                    message="Domain is required when ingress is enabled",
                    field="ingress.domain"
                ))
            elif not self.domain_pattern.match(ingress.domain):
                report.add_result(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="ingress",
                    message="Invalid domain format",
                    field="ingress.domain",
                    suggestion="Use a valid domain name format"
                ))
            
            if not ingress.path.startswith('/'):
                report.add_result(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="ingress",
                    message="Ingress path must start with '/'",
                    field="ingress.path"
                ))
            
            if not ingress.tls:
                report.add_result(ValidationResult(
                    level=ValidationLevel.RECOMMENDATION,
                    category="security",
                    message="Consider enabling TLS for production deployments",
                    field="ingress.tls",
                    suggestion="Enable TLS for better security"
                ))
    
    def _validate_autopilot_compatibility(self, app_config: AppConfig, report: ValidationReport) -> None:
        """Validate GKE Autopilot specific compatibility"""
        
        # Check for unsupported features
        if app_config.scaling_config.min_replicas == 0:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="autopilot",
                message="GKE Autopilot does not support zero replicas",
                field="scaling.min_replicas",
                suggestion="Set minimum replicas to at least 1"
            ))
        
        # Check resource optimization opportunities
        cpu_millicores = self._parse_cpu_to_millicores(app_config.resource_requests.cpu)
        memory_mb = self._parse_memory_to_mb(app_config.resource_requests.memory)
        
        if cpu_millicores and cpu_millicores < 250:
            report.add_result(ValidationResult(
                level=ValidationLevel.RECOMMENDATION,
                category="autopilot",
                message="Consider increasing CPU to 250m for better Autopilot node utilization",
                field="resources.cpu"
            ))
        
        if memory_mb and memory_mb < 512:
            report.add_result(ValidationResult(
                level=ValidationLevel.RECOMMENDATION,
                category="autopilot",
                message="Consider increasing memory to 512Mi for better Autopilot node utilization",
                field="resources.memory"
            ))
        
        # Check for Autopilot best practices
        if not app_config.health_checks.path:
            report.add_result(ValidationResult(
                level=ValidationLevel.RECOMMENDATION,
                category="autopilot",
                message="Health checks are recommended for Autopilot deployments",
                field="health_checks",
                suggestion="Add readiness and liveness probes"
            ))
    
    def _validate_security_config(self, app_config: AppConfig, report: ValidationReport) -> None:
        """Validate security configuration"""
        
        # Check for secrets in environment variables
        for env_name, env_value in app_config.environment_variables.items():
            if any(keyword in env_name.lower() for keyword in ['password', 'secret', 'key', 'token']):
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="security",
                    message=f"Environment variable '{env_name}' appears to contain sensitive data",
                    field="environment_variables",
                    suggestion="Use Kubernetes secrets for sensitive data"
                ))
        
        # Check for latest tag usage
        if app_config.image.endswith(':latest'):
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="security",
                message="Using 'latest' tag is not recommended for production",
                field="image",
                suggestion="Use specific version tags for reproducible deployments"
            ))
        
        # Check for privileged ports
        if app_config.port < 1024:
            report.add_result(ValidationResult(
                level=ValidationLevel.WARNING,
                category="security",
                message="Using privileged port may require additional permissions",
                field="port",
                suggestion="Consider using non-privileged ports (>= 1024)"
            ))
    
    async def _validate_container_image(self, image: str, report: ValidationReport) -> None:
        """Validate container image accessibility and security"""
        
        if not self.session:
            return
        
        try:
            # Basic image format validation
            if ':' not in image and '@' not in image:
                report.add_result(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="image",
                    message="Image tag not specified, will default to 'latest'",
                    field="image",
                    suggestion="Specify explicit image tag"
                ))
            
            # Check for common registries
            if image.startswith('gcr.io/') or image.startswith('us.gcr.io/'):
                report.add_result(ValidationResult(
                    level=ValidationLevel.INFO,
                    category="image",
                    message="Using Google Container Registry (recommended for GKE)",
                    field="image"
                ))
            elif image.startswith('docker.io/') or '/' not in image.split(':')[0]:
                report.add_result(ValidationResult(
                    level=ValidationLevel.INFO,
                    category="image",
                    message="Using Docker Hub registry",
                    field="image"
                ))
            
            # TODO: Add actual image accessibility check
            # This would require authentication and registry-specific APIs
            
        except Exception as e:
            logger.warning(f"Failed to validate container image: {e}")
    
    def _parse_cpu_to_millicores(self, cpu_str: str) -> Optional[int]:
        """Parse CPU string to millicores"""
        try:
            if cpu_str.endswith('m'):
                return int(cpu_str[:-1])
            else:
                return int(float(cpu_str) * 1000)
        except (ValueError, TypeError):
            return None
    
    def _parse_memory_to_mb(self, memory_str: str) -> Optional[int]:
        """Parse memory string to MB"""
        try:
            if memory_str.endswith('Mi'):
                return int(memory_str[:-2])
            elif memory_str.endswith('Gi'):
                return int(memory_str[:-2]) * 1024
            elif memory_str.endswith('Ki'):
                return int(memory_str[:-2]) // 1024
            elif memory_str.endswith('M'):
                return int(memory_str[:-1])
            elif memory_str.endswith('G'):
                return int(memory_str[:-1]) * 1000
            elif memory_str.endswith('K'):
                return int(memory_str[:-1]) // 1000
            else:
                return int(memory_str) // (1024 * 1024)  # Assume bytes
        except (ValueError, TypeError):
            return None
    
    def _parse_storage_to_gb(self, storage_str: str) -> Optional[int]:
        """Parse storage string to GB"""
        try:
            if storage_str.endswith('Gi'):
                return int(storage_str[:-2])
            elif storage_str.endswith('Ti'):
                return int(storage_str[:-2]) * 1024
            elif storage_str.endswith('Mi'):
                return int(storage_str[:-2]) // 1024
            elif storage_str.endswith('G'):
                return int(storage_str[:-1])
            elif storage_str.endswith('T'):
                return int(storage_str[:-1]) * 1000
            elif storage_str.endswith('M'):
                return int(storage_str[:-1]) // 1000
            else:
                return int(storage_str) // (1024 ** 3)  # Assume bytes
        except (ValueError, TypeError):
            return None
    
    async def validate_cluster_config(self, cluster_config: ClusterConfig) -> ValidationReport:
        """
        Validate cluster configuration.
        
        Args:
            cluster_config: Cluster configuration to validate
            
        Returns:
            ValidationReport: Detailed validation results
        """
        logger.info(f"Validating cluster configuration: {cluster_config.name}")
        
        report = ValidationReport()
        
        # Basic cluster validation
        if not cluster_config.name:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="cluster",
                message="Cluster name is required",
                field="name"
            ))
        elif not self.naming_pattern.match(cluster_config.name):
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="cluster",
                message="Cluster name must be lowercase alphanumeric with hyphens",
                field="name"
            ))
        elif len(cluster_config.name) > 40:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="cluster",
                message="Cluster name must be 40 characters or less",
                field="name"
            ))
        
        # Region validation
        if not cluster_config.region:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="cluster",
                message="Region is required",
                field="region"
            ))
        
        # Network configuration validation
        self._validate_network_config(cluster_config.network_config, report)
        
        # Security configuration validation
        self._validate_security_cluster_config(cluster_config.security_config, report)
        
        logger.info(f"Cluster validation completed: {len(report.results)} issues found")
        return report
    
    def _validate_network_config(self, network_config, report: ValidationReport) -> None:
        """Validate network configuration"""
        
        # CIDR validation
        import ipaddress
        
        try:
            ipaddress.IPv4Network(network_config.master_ipv4_cidr_block)
        except ipaddress.AddressValueError:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="network",
                message="Invalid master IPv4 CIDR block",
                field="network.master_ipv4_cidr_block"
            ))
        
        try:
            ipaddress.IPv4Network(network_config.pod_cidr)
        except ipaddress.AddressValueError:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="network",
                message="Invalid pod CIDR block",
                field="network.pod_cidr"
            ))
        
        try:
            ipaddress.IPv4Network(network_config.service_cidr)
        except ipaddress.AddressValueError:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="network",
                message="Invalid service CIDR block",
                field="network.service_cidr"
            ))
    
    def _validate_security_cluster_config(self, security_config, report: ValidationReport) -> None:
        """Validate security configuration for cluster"""
        
        if security_config.service_account and '@' not in security_config.service_account:
            report.add_result(ValidationResult(
                level=ValidationLevel.ERROR,
                category="security",
                message="Service account must be in email format",
                field="security.service_account"
            ))
        
        if not security_config.enable_workload_identity:
            report.add_result(ValidationResult(
                level=ValidationLevel.RECOMMENDATION,
                category="security",
                message="Workload Identity is recommended for better security",
                field="security.enable_workload_identity",
                suggestion="Enable Workload Identity for secure pod-to-GCP service communication"
            ))
        
        if not security_config.enable_network_policy:
            report.add_result(ValidationResult(
                level=ValidationLevel.RECOMMENDATION,
                category="security",
                message="Network Policy is recommended for network security",
                field="security.enable_network_policy",
                suggestion="Enable Network Policy for micro-segmentation"
            ))
    
    def generate_validation_summary(self, report: ValidationReport) -> str:
        """Generate human-readable validation summary"""
        
        summary = []
        
        if report.valid:
            summary.append("✅ Configuration is valid")
        else:
            summary.append("❌ Configuration has errors that must be fixed")
        
        errors = report.get_errors()
        warnings = report.get_warnings()
        recommendations = report.get_recommendations()
        
        if errors:
            summary.append(f"\n🚨 {len(errors)} Error(s):")
            for error in errors:
                summary.append(f"  • {error.message}")
                if error.suggestion:
                    summary.append(f"    💡 {error.suggestion}")
        
        if warnings:
            summary.append(f"\n⚠️  {len(warnings)} Warning(s):")
            for warning in warnings:
                summary.append(f"  • {warning.message}")
                if warning.suggestion:
                    summary.append(f"    💡 {warning.suggestion}")
        
        if recommendations:
            summary.append(f"\n💡 {len(recommendations)} Recommendation(s):")
            for rec in recommendations:
                summary.append(f"  • {rec.message}")
                if rec.suggestion:
                    summary.append(f"    💡 {rec.suggestion}")
        
        return "\n".join(summary)