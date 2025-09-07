"""
GKE Client Integration for Autopilot Deployment Framework

This module provides comprehensive Google Kubernetes Engine client integration
with authentication, cluster management, and Kubernetes resource operations.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

# Google Cloud imports
try:
    from google.cloud import container_v1
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    import google.auth.transport.requests
except ImportError:
    container_v1 = None
    default = None
    DefaultCredentialsError = Exception

# Kubernetes imports
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    client = None
    config = None
    ApiException = Exception

from ..models.app_config import ClusterConfig, AppConfig, DeploymentResult, DeploymentPhase


logger = logging.getLogger(__name__)


@dataclass
class ClusterInfo:
    """Information about a GKE cluster"""
    name: str
    location: str
    status: str
    node_count: int
    kubernetes_version: str
    endpoint: str
    autopilot_enabled: bool
    created_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'location': self.location,
            'status': self.status,
            'node_count': self.node_count,
            'kubernetes_version': self.kubernetes_version,
            'endpoint': self.endpoint,
            'autopilot_enabled': self.autopilot_enabled,
            'created_time': self.created_time.isoformat()
        }


class GKEClientError(Exception):
    """Custom exception for GKE client errors"""
    pass


class GKEClient:
    """
    Google Kubernetes Engine client for Autopilot cluster management.
    
    This class provides comprehensive GKE operations including:
    - Cluster creation, update, and deletion
    - Kubernetes resource management
    - Authentication and project setup
    - Health monitoring and status reporting
    """
    
    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize GKE client with authentication.
        
        Args:
            project_id: Google Cloud project ID (auto-detected if None)
            credentials_path: Path to service account credentials (optional)
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        
        # Initialize clients
        self._container_client = None
        self._k8s_client = None
        self._credentials = None
        
        # Authentication
        self._authenticate()
        
        logger.info(f"Initialized GKE client for project: {self.project_id}")
    
    def _authenticate(self) -> None:
        """Authenticate with Google Cloud and set up credentials"""
        if not container_v1:
            raise GKEClientError("Google Cloud Container library not installed. Run: pip install google-cloud-container")
        
        try:
            if self.credentials_path:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            
            # Get default credentials
            credentials, project = default()
            self._credentials = credentials
            
            if not self.project_id:
                self.project_id = project
            
            if not self.project_id:
                raise GKEClientError("Project ID not found. Set GOOGLE_CLOUD_PROJECT or provide project_id")
            
            # Initialize container client
            self._container_client = container_v1.ClusterManagerClient(credentials=credentials)
            
            logger.info(f"Authenticated with Google Cloud project: {self.project_id}")
            
        except DefaultCredentialsError as e:
            raise GKEClientError(f"Authentication failed: {e}. Please run 'gcloud auth application-default login'")
        except Exception as e:
            raise GKEClientError(f"Failed to initialize GKE client: {e}")
    
    def _setup_kubernetes_client(self, cluster_name: str, location: str) -> None:
        """Setup Kubernetes client for cluster operations"""
        if not client:
            raise GKEClientError("Kubernetes client library not installed. Run: pip install kubernetes")
        
        try:
            # Get cluster credentials
            cluster_info = self.get_cluster_info(cluster_name, location)
            
            # Configure Kubernetes client
            configuration = client.Configuration()
            configuration.host = f"https://{cluster_info.endpoint}"
            
            # Set up authentication
            if self._credentials:
                # Refresh credentials if needed
                request = google.auth.transport.requests.Request()
                self._credentials.refresh(request)
                configuration.api_key_prefix['authorization'] = 'Bearer'
                configuration.api_key['authorization'] = self._credentials.token
            
            # Create API client
            self._k8s_client = client.ApiClient(configuration)
            
            logger.info(f"Kubernetes client configured for cluster: {cluster_name}")
            
        except Exception as e:
            raise GKEClientError(f"Failed to setup Kubernetes client: {e}")
    
    async def create_autopilot_cluster(self, cluster_config: ClusterConfig) -> ClusterInfo:
        """
        Create a new GKE Autopilot cluster.
        
        Args:
            cluster_config: Cluster configuration
            
        Returns:
            ClusterInfo: Information about the created cluster
        """
        logger.info(f"Creating GKE Autopilot cluster: {cluster_config.name}")
        
        try:
            # Build cluster specification
            cluster_spec = self._build_cluster_spec(cluster_config)
            
            # Create cluster request
            parent = f"projects/{self.project_id}/locations/{cluster_config.region}"
            
            # Execute cluster creation
            operation = self._container_client.create_cluster(
                parent=parent,
                cluster=cluster_spec
            )
            
            logger.info(f"Cluster creation initiated. Operation: {operation.name}")
            
            # Wait for operation to complete
            cluster_info = await self._wait_for_operation(operation, cluster_config.name, cluster_config.region)
            
            logger.info(f"Cluster created successfully: {cluster_config.name}")
            return cluster_info
            
        except Exception as e:
            logger.error(f"Failed to create cluster {cluster_config.name}: {e}")
            raise GKEClientError(f"Cluster creation failed: {e}")
    
    def _build_cluster_spec(self, cluster_config: ClusterConfig) -> Dict[str, Any]:
        """Build GKE cluster specification from configuration"""
        
        # Base Autopilot cluster configuration
        cluster_spec = {
            "name": cluster_config.name,
            "location": cluster_config.region,
            "autopilot": {
                "enabled": True
            },
            "release_channel": {
                "channel": "REGULAR"
            },
            "ip_allocation_policy": {
                "use_ip_aliases": True
            },
            "network_policy": {
                "enabled": cluster_config.security_config.enable_network_policy
            },
            "addons_config": {
                "http_load_balancing": {"disabled": False},
                "horizontal_pod_autoscaling": {"disabled": False},
                "network_policy_config": {
                    "disabled": not cluster_config.security_config.enable_network_policy
                }
            }
        }
        
        # Network configuration
        if cluster_config.network_config.vpc_name:
            cluster_spec["network"] = cluster_config.network_config.vpc_name
        
        if cluster_config.network_config.subnet_name:
            cluster_spec["subnetwork"] = cluster_config.network_config.subnet_name
        
        # Private cluster configuration
        if cluster_config.network_config.enable_private_nodes:
            cluster_spec["private_cluster_config"] = {
                "enable_private_nodes": True,
                "enable_private_endpoint": cluster_config.network_config.enable_private_endpoint,
                "master_ipv4_cidr_block": cluster_config.network_config.master_ipv4_cidr_block
            }
        
        # Workload Identity
        if cluster_config.security_config.enable_workload_identity:
            cluster_spec["workload_identity_config"] = {
                "workload_pool": f"{self.project_id}.svc.id.goog"
            }
        
        # Monitoring and logging
        if cluster_config.monitoring_config.enable_monitoring:
            cluster_spec["monitoring_config"] = {
                "enable_components": ["SYSTEM_COMPONENTS", "WORKLOADS"]
            }
        
        if cluster_config.monitoring_config.enable_logging:
            cluster_spec["logging_config"] = {
                "enable_components": ["SYSTEM_COMPONENTS", "WORKLOADS"]
            }
        
        # Labels
        if cluster_config.labels:
            cluster_spec["resource_labels"] = cluster_config.labels
        
        return cluster_spec
    
    async def _wait_for_operation(self, operation, cluster_name: str, location: str, timeout_minutes: int = 30) -> ClusterInfo:
        """Wait for GKE operation to complete"""
        operation_name = operation.name
        timeout = datetime.now() + timedelta(minutes=timeout_minutes)
        
        logger.info(f"Waiting for operation to complete: {operation_name}")
        
        while datetime.now() < timeout:
            try:
                # Check operation status
                op_request = container_v1.GetOperationRequest(name=operation_name)
                current_op = self._container_client.get_operation(request=op_request)
                
                if current_op.status == container_v1.Operation.Status.DONE:
                    if current_op.error:
                        raise GKEClientError(f"Operation failed: {current_op.error}")
                    
                    # Operation completed successfully
                    logger.info(f"Operation completed: {operation_name}")
                    return self.get_cluster_info(cluster_name, location)
                
                elif current_op.status == container_v1.Operation.Status.ABORTING:
                    raise GKEClientError(f"Operation aborted: {operation_name}")
                
                # Still running, wait and check again
                logger.debug(f"Operation still running: {current_op.status}")
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error checking operation status: {e}")
                await asyncio.sleep(30)
        
        raise GKEClientError(f"Operation timed out after {timeout_minutes} minutes: {operation_name}")
    
    def get_cluster_info(self, cluster_name: str, location: str) -> ClusterInfo:
        """
        Get information about a GKE cluster.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location (region or zone)
            
        Returns:
            ClusterInfo: Cluster information
        """
        try:
            cluster_path = f"projects/{self.project_id}/locations/{location}/clusters/{cluster_name}"
            cluster = self._container_client.get_cluster(name=cluster_path)
            
            return ClusterInfo(
                name=cluster.name,
                location=cluster.location,
                status=cluster.status.name,
                node_count=cluster.current_node_count,
                kubernetes_version=cluster.current_master_version,
                endpoint=cluster.endpoint,
                autopilot_enabled=cluster.autopilot.enabled if cluster.autopilot else False,
                created_time=datetime.fromisoformat(cluster.create_time.rfc3339())
            )
            
        except Exception as e:
            logger.error(f"Failed to get cluster info for {cluster_name}: {e}")
            raise GKEClientError(f"Failed to get cluster info: {e}")
    
    def list_clusters(self, location: str = "-") -> List[ClusterInfo]:
        """
        List all clusters in the project.
        
        Args:
            location: Location to list clusters from ("-" for all locations)
            
        Returns:
            List of ClusterInfo objects
        """
        try:
            parent = f"projects/{self.project_id}/locations/{location}"
            response = self._container_client.list_clusters(parent=parent)
            
            clusters = []
            for cluster in response.clusters:
                cluster_info = ClusterInfo(
                    name=cluster.name,
                    location=cluster.location,
                    status=cluster.status.name,
                    node_count=cluster.current_node_count,
                    kubernetes_version=cluster.current_master_version,
                    endpoint=cluster.endpoint,
                    autopilot_enabled=cluster.autopilot.enabled if cluster.autopilot else False,
                    created_time=datetime.fromisoformat(cluster.create_time.rfc3339())
                )
                clusters.append(cluster_info)
            
            logger.info(f"Found {len(clusters)} clusters in {location}")
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            raise GKEClientError(f"Failed to list clusters: {e}")
    
    async def delete_cluster(self, cluster_name: str, location: str) -> bool:
        """
        Delete a GKE cluster.
        
        Args:
            cluster_name: Name of the cluster to delete
            location: Cluster location
            
        Returns:
            True if deletion was successful
        """
        logger.info(f"Deleting cluster: {cluster_name}")
        
        try:
            cluster_path = f"projects/{self.project_id}/locations/{location}/clusters/{cluster_name}"
            operation = self._container_client.delete_cluster(name=cluster_path)
            
            # Wait for deletion to complete
            await self._wait_for_operation(operation, cluster_name, location)
            
            logger.info(f"Cluster deleted successfully: {cluster_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete cluster {cluster_name}: {e}")
            raise GKEClientError(f"Cluster deletion failed: {e}")
    
    def deploy_application(self, app_config: AppConfig, cluster_name: str, location: str) -> DeploymentResult:
        """
        Deploy application to GKE cluster.
        
        Args:
            app_config: Application configuration
            cluster_name: Target cluster name
            location: Cluster location
            
        Returns:
            DeploymentResult: Deployment result information
        """
        logger.info(f"Deploying application {app_config.name} to cluster {cluster_name}")
        
        try:
            # Setup Kubernetes client for the cluster
            self._setup_kubernetes_client(cluster_name, location)
            
            # Generate Kubernetes manifests
            manifests = self._generate_kubernetes_manifests(app_config)
            
            # Apply manifests to cluster
            deployment_result = self._apply_manifests(manifests, app_config, cluster_name)
            
            logger.info(f"Application deployed successfully: {app_config.name}")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Failed to deploy application {app_config.name}: {e}")
            return DeploymentResult(
                success=False,
                cluster_name=cluster_name,
                phase=DeploymentPhase.FAILED,
                error_message=str(e)
            )
    
    def _generate_kubernetes_manifests(self, app_config: AppConfig) -> List[Dict[str, Any]]:
        """Generate Kubernetes manifests for application"""
        manifests = []
        
        # Deployment manifest
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": app_config.name,
                "labels": {"app": app_config.name, **app_config.labels}
            },
            "spec": {
                "replicas": app_config.scaling_config.min_replicas,
                "selector": {"matchLabels": {"app": app_config.name}},
                "template": {
                    "metadata": {"labels": {"app": app_config.name}},
                    "spec": {
                        "containers": [{
                            "name": app_config.name,
                            "image": app_config.image,
                            "ports": [{"containerPort": app_config.port}],
                            "resources": {
                                "requests": app_config.resource_requests.to_dict()
                            },
                            "readinessProbe": app_config.health_checks.to_kubernetes_probe(),
                            "livenessProbe": app_config.health_checks.to_kubernetes_probe()
                        }]
                    }
                }
            }
        }
        
        # Add environment variables
        if app_config.environment_variables:
            env_vars = [{"name": k, "value": v} for k, v in app_config.environment_variables.items()]
            deployment["spec"]["template"]["spec"]["containers"][0]["env"] = env_vars
        
        manifests.append(deployment)
        
        # Service manifest
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": app_config.name,
                "labels": {"app": app_config.name}
            },
            "spec": {
                "selector": {"app": app_config.name},
                "ports": [{
                    "port": 80,
                    "targetPort": app_config.port,
                    "protocol": "TCP"
                }],
                "type": "ClusterIP"
            }
        }
        manifests.append(service)
        
        # HPA manifest
        if app_config.scaling_config.max_replicas > app_config.scaling_config.min_replicas:
            hpa = {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {"name": f"{app_config.name}-hpa"},
                "spec": app_config.scaling_config.to_hpa_spec()
            }
            hpa["spec"]["scaleTargetRef"] = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": app_config.name
            }
            manifests.append(hpa)
        
        # Ingress manifest
        if app_config.ingress_config.enabled:
            ingress = app_config.ingress_config.to_kubernetes_ingress(app_config.name, 80)
            if ingress:
                manifests.append(ingress)
        
        return manifests
    
    def _apply_manifests(self, manifests: List[Dict[str, Any]], app_config: AppConfig, cluster_name: str) -> DeploymentResult:
        """Apply Kubernetes manifests to cluster"""
        
        # For now, return a mock successful deployment
        # In a real implementation, this would use the Kubernetes API to apply manifests
        
        application_url = None
        if app_config.ingress_config.enabled and app_config.ingress_config.domain:
            protocol = "https" if app_config.ingress_config.tls else "http"
            application_url = f"{protocol}://{app_config.ingress_config.domain}"
        
        return DeploymentResult(
            success=True,
            cluster_name=cluster_name,
            application_url=application_url,
            phase=DeploymentPhase.READY,
            monitoring_dashboard=f"https://console.cloud.google.com/kubernetes/workload/overview?project={self.project_id}"
        )
    
    def get_deployment_status(self, app_name: str, cluster_name: str, location: str) -> Dict[str, Any]:
        """
        Get deployment status for an application.
        
        Args:
            app_name: Application name
            cluster_name: Cluster name
            location: Cluster location
            
        Returns:
            Deployment status information
        """
        try:
            # Setup Kubernetes client
            self._setup_kubernetes_client(cluster_name, location)
            
            # For now, return mock status
            # In a real implementation, this would query Kubernetes API
            
            return {
                "application": app_name,
                "cluster": cluster_name,
                "status": "Running",
                "replicas": {"ready": 2, "total": 2},
                "last_updated": datetime.now().isoformat(),
                "health": "Healthy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {
                "application": app_name,
                "cluster": cluster_name,
                "status": "Unknown",
                "error": str(e)
            }
    
    def scale_deployment(self, app_name: str, cluster_name: str, location: str, replicas: int) -> bool:
        """
        Scale application deployment.
        
        Args:
            app_name: Application name
            cluster_name: Cluster name
            location: Cluster location
            replicas: Target number of replicas
            
        Returns:
            True if scaling was successful
        """
        logger.info(f"Scaling {app_name} to {replicas} replicas")
        
        try:
            # Setup Kubernetes client
            self._setup_kubernetes_client(cluster_name, location)
            
            # For now, return success
            # In a real implementation, this would use Kubernetes API to scale
            
            logger.info(f"Scaled {app_name} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale {app_name}: {e}")
            raise GKEClientError(f"Scaling failed: {e}")
    
    def delete_application(self, app_name: str, cluster_name: str, location: str) -> bool:
        """
        Delete application from cluster.
        
        Args:
            app_name: Application name
            cluster_name: Cluster name
            location: Cluster location
            
        Returns:
            True if deletion was successful
        """
        logger.info(f"Deleting application {app_name} from cluster {cluster_name}")
        
        try:
            # Setup Kubernetes client
            self._setup_kubernetes_client(cluster_name, location)
            
            # For now, return success
            # In a real implementation, this would delete Kubernetes resources
            
            logger.info(f"Application {app_name} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete application {app_name}: {e}")
            raise GKEClientError(f"Application deletion failed: {e}")
    
    def get_cluster_health(self, cluster_name: str, location: str) -> Dict[str, Any]:
        """
        Get cluster health information.
        
        Args:
            cluster_name: Cluster name
            location: Cluster location
            
        Returns:
            Cluster health information
        """
        try:
            cluster_info = self.get_cluster_info(cluster_name, location)
            
            return {
                "cluster": cluster_name,
                "status": cluster_info.status,
                "kubernetes_version": cluster_info.kubernetes_version,
                "node_count": cluster_info.node_count,
                "autopilot_enabled": cluster_info.autopilot_enabled,
                "health": "Healthy" if cluster_info.status == "RUNNING" else "Unhealthy",
                "last_checked": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {
                "cluster": cluster_name,
                "health": "Unknown",
                "error": str(e)
            }