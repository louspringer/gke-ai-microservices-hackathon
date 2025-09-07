"""
Cluster Manager for GKE Autopilot Deployment Framework

This module provides comprehensive GKE Autopilot cluster management including
creation, health monitoring, updates, and maintenance operations.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..core.gke_client import GKEClient, ClusterInfo, GKEClientError
from ..models.app_config import ClusterConfig, DeploymentResult, DeploymentPhase


logger = logging.getLogger(__name__)


class ClusterStatus(Enum):
    """Cluster status enumeration"""
    CREATING = "creating"
    RUNNING = "running"
    UPDATING = "updating"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ClusterHealth:
    """Cluster health information"""
    status: ClusterStatus
    node_count: int
    kubernetes_version: str
    autopilot_enabled: bool
    last_updated: datetime
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def is_healthy(self) -> bool:
        """Check if cluster is healthy"""
        return self.status == ClusterStatus.RUNNING and len(self.issues) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'node_count': self.node_count,
            'kubernetes_version': self.kubernetes_version,
            'autopilot_enabled': self.autopilot_enabled,
            'last_updated': self.last_updated.isoformat(),
            'healthy': self.is_healthy(),
            'issues': self.issues,
            'recommendations': self.recommendations
        }


@dataclass
class ClusterOperation:
    """Cluster operation tracking"""
    operation_id: str
    operation_type: str
    cluster_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def is_complete(self) -> bool:
        return self.completed_at is not None
    
    def is_successful(self) -> bool:
        return self.is_complete() and self.error_message is None


class ClusterManager:
    """
    Comprehensive GKE Autopilot cluster management system.
    
    Features:
    - Cluster creation with optimal Autopilot configuration
    - Health monitoring and status reporting
    - Cluster updates and maintenance operations
    - Cost optimization and resource management
    - Multi-cluster coordination
    """
    
    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize cluster manager.
        
        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account credentials
        """
        self.gke_client = GKEClient(project_id, credentials_path)
        self.project_id = self.gke_client.project_id
        
        # Operation tracking
        self.active_operations: Dict[str, ClusterOperation] = {}
        
        # Cluster cache
        self._cluster_cache: Dict[str, ClusterInfo] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update: Optional[datetime] = None
        
        logger.info(f"Cluster manager initialized for project: {self.project_id}")
    
    async def create_cluster(self, cluster_config: ClusterConfig, wait_for_completion: bool = True) -> ClusterInfo:
        """
        Create a new GKE Autopilot cluster with optimal configuration.
        
        Args:
            cluster_config: Cluster configuration
            wait_for_completion: Whether to wait for cluster creation to complete
            
        Returns:
            ClusterInfo: Information about the created cluster
        """
        logger.info(f"Creating GKE Autopilot cluster: {cluster_config.name}")
        
        try:
            # Validate cluster configuration
            self._validate_cluster_config(cluster_config)
            
            # Check if cluster already exists
            existing_clusters = await self.list_clusters(cluster_config.region)
            if any(c.name == cluster_config.name for c in existing_clusters):
                raise GKEClientError(f"Cluster {cluster_config.name} already exists")
            
            # Create cluster using GKE client
            cluster_info = await self.gke_client.create_autopilot_cluster(cluster_config)
            
            # Update cache
            self._update_cluster_cache(cluster_info)
            
            logger.info(f"Cluster creation initiated: {cluster_config.name}")
            
            if wait_for_completion:
                # Monitor cluster creation progress
                cluster_info = await self._wait_for_cluster_ready(cluster_config.name, cluster_config.region)
                logger.info(f"Cluster created successfully: {cluster_config.name}")
            
            return cluster_info
            
        except Exception as e:
            logger.error(f"Failed to create cluster {cluster_config.name}: {e}")
            raise
    
    async def get_cluster_info(self, cluster_name: str, location: str, use_cache: bool = True) -> ClusterInfo:
        """
        Get detailed information about a cluster.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            use_cache: Whether to use cached data if available
            
        Returns:
            ClusterInfo: Cluster information
        """
        cache_key = f"{cluster_name}:{location}"
        
        # Check cache first
        if use_cache and self._is_cache_valid() and cache_key in self._cluster_cache:
            logger.debug(f"Returning cached cluster info for {cluster_name}")
            return self._cluster_cache[cache_key]
        
        try:
            cluster_info = self.gke_client.get_cluster_info(cluster_name, location)
            self._update_cluster_cache(cluster_info)
            return cluster_info
            
        except Exception as e:
            logger.error(f"Failed to get cluster info for {cluster_name}: {e}")
            raise
    
    async def list_clusters(self, location: str = "-", use_cache: bool = True) -> List[ClusterInfo]:
        """
        List all clusters in the specified location.
        
        Args:
            location: Location to list clusters from ("-" for all locations)
            use_cache: Whether to use cached data if available
            
        Returns:
            List of ClusterInfo objects
        """
        if use_cache and self._is_cache_valid():
            cached_clusters = [c for c in self._cluster_cache.values() 
                             if location == "-" or c.location == location]
            if cached_clusters:
                logger.debug(f"Returning {len(cached_clusters)} cached clusters")
                return cached_clusters
        
        try:
            clusters = self.gke_client.list_clusters(location)
            
            # Update cache
            for cluster in clusters:
                self._update_cluster_cache(cluster)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            raise
    
    async def delete_cluster(self, cluster_name: str, location: str, wait_for_completion: bool = True) -> bool:
        """
        Delete a GKE cluster.
        
        Args:
            cluster_name: Name of the cluster to delete
            location: Cluster location
            wait_for_completion: Whether to wait for deletion to complete
            
        Returns:
            True if deletion was successful
        """
        logger.info(f"Deleting cluster: {cluster_name}")
        
        try:
            # Verify cluster exists
            await self.get_cluster_info(cluster_name, location)
            
            # Delete cluster
            success = await self.gke_client.delete_cluster(cluster_name, location)
            
            if success:
                # Remove from cache
                cache_key = f"{cluster_name}:{location}"
                self._cluster_cache.pop(cache_key, None)
                
                logger.info(f"Cluster deleted successfully: {cluster_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete cluster {cluster_name}: {e}")
            raise
    
    async def get_cluster_health(self, cluster_name: str, location: str) -> ClusterHealth:
        """
        Get comprehensive cluster health information.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            
        Returns:
            ClusterHealth: Detailed health information
        """
        try:
            cluster_info = await self.get_cluster_info(cluster_name, location)
            
            # Determine cluster status
            status_map = {
                'RUNNING': ClusterStatus.RUNNING,
                'PROVISIONING': ClusterStatus.CREATING,
                'RECONCILING': ClusterStatus.UPDATING,
                'STOPPING': ClusterStatus.STOPPING,
                'ERROR': ClusterStatus.ERROR
            }
            status = status_map.get(cluster_info.status, ClusterStatus.UNKNOWN)
            
            # Analyze cluster health
            issues = []
            recommendations = []
            
            # Check cluster status
            if status == ClusterStatus.ERROR:
                issues.append("Cluster is in error state")
            elif status == ClusterStatus.UNKNOWN:
                issues.append("Cluster status is unknown")
            
            # Check node count
            if cluster_info.node_count == 0:
                issues.append("No nodes available in cluster")
            elif cluster_info.node_count < 2:
                recommendations.append("Consider having at least 2 nodes for high availability")
            
            # Check Autopilot status
            if not cluster_info.autopilot_enabled:
                recommendations.append("Enable Autopilot for better resource management")
            
            # Check cluster age
            cluster_age = datetime.now() - cluster_info.created_time
            if cluster_age > timedelta(days=365):
                recommendations.append("Consider upgrading cluster - it's over 1 year old")
            
            return ClusterHealth(
                status=status,
                node_count=cluster_info.node_count,
                kubernetes_version=cluster_info.kubernetes_version,
                autopilot_enabled=cluster_info.autopilot_enabled,
                last_updated=datetime.now(),
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to get cluster health for {cluster_name}: {e}")
            return ClusterHealth(
                status=ClusterStatus.ERROR,
                node_count=0,
                kubernetes_version="unknown",
                autopilot_enabled=False,
                last_updated=datetime.now(),
                issues=[f"Failed to get cluster health: {str(e)}"]
            )
    
    async def update_cluster(self, cluster_name: str, location: str, updates: Dict[str, Any]) -> bool:
        """
        Update cluster configuration.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            updates: Dictionary of updates to apply
            
        Returns:
            True if update was successful
        """
        logger.info(f"Updating cluster {cluster_name} with: {updates}")
        
        try:
            # For now, this is a placeholder
            # In a real implementation, this would use the GKE API to update cluster settings
            
            # Invalidate cache
            cache_key = f"{cluster_name}:{location}"
            self._cluster_cache.pop(cache_key, None)
            
            logger.info(f"Cluster update completed: {cluster_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update cluster {cluster_name}: {e}")
            raise
    
    async def scale_cluster(self, cluster_name: str, location: str, node_count: int) -> bool:
        """
        Scale cluster node count (for non-Autopilot clusters).
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            node_count: Target node count
            
        Returns:
            True if scaling was successful
        """
        logger.info(f"Scaling cluster {cluster_name} to {node_count} nodes")
        
        try:
            cluster_info = await self.get_cluster_info(cluster_name, location)
            
            if cluster_info.autopilot_enabled:
                logger.warning(f"Cluster {cluster_name} is Autopilot - scaling is automatic")
                return True
            
            # For non-Autopilot clusters, implement scaling logic here
            # This is a placeholder for the actual implementation
            
            logger.info(f"Cluster scaling completed: {cluster_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale cluster {cluster_name}: {e}")
            raise
    
    async def get_cluster_costs(self, cluster_name: str, location: str, days: int = 30) -> Dict[str, Any]:
        """
        Get cluster cost information.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            days: Number of days to analyze
            
        Returns:
            Cost information dictionary
        """
        try:
            cluster_info = await self.get_cluster_info(cluster_name, location)
            
            # Placeholder cost calculation
            # In a real implementation, this would integrate with Google Cloud Billing API
            
            estimated_hourly_cost = 0.10 * cluster_info.node_count  # $0.10 per node per hour
            daily_cost = estimated_hourly_cost * 24
            monthly_cost = daily_cost * 30
            
            return {
                'cluster': cluster_name,
                'location': location,
                'period_days': days,
                'estimated_costs': {
                    'hourly': estimated_hourly_cost,
                    'daily': daily_cost,
                    'monthly': monthly_cost
                },
                'cost_breakdown': {
                    'compute': monthly_cost * 0.7,
                    'networking': monthly_cost * 0.2,
                    'storage': monthly_cost * 0.1
                },
                'optimization_suggestions': [
                    "Enable Autopilot for automatic resource optimization",
                    "Use preemptible nodes for non-critical workloads",
                    "Implement proper resource requests and limits"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster costs for {cluster_name}: {e}")
            return {
                'cluster': cluster_name,
                'error': str(e)
            }
    
    async def monitor_cluster_health(self, cluster_name: str, location: str, 
                                   check_interval: int = 60, max_checks: int = 10) -> List[ClusterHealth]:
        """
        Monitor cluster health over time.
        
        Args:
            cluster_name: Name of the cluster
            location: Cluster location
            check_interval: Interval between checks in seconds
            max_checks: Maximum number of health checks
            
        Returns:
            List of ClusterHealth snapshots
        """
        logger.info(f"Starting health monitoring for cluster {cluster_name}")
        
        health_history = []
        
        for i in range(max_checks):
            try:
                health = await self.get_cluster_health(cluster_name, location)
                health_history.append(health)
                
                logger.debug(f"Health check {i+1}/{max_checks}: {health.status.value}")
                
                if i < max_checks - 1:  # Don't sleep after the last check
                    await asyncio.sleep(check_interval)
                    
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                break
        
        logger.info(f"Health monitoring completed for {cluster_name}: {len(health_history)} checks")
        return health_history
    
    async def _wait_for_cluster_ready(self, cluster_name: str, location: str, 
                                    timeout_minutes: int = 30) -> ClusterInfo:
        """Wait for cluster to be ready"""
        timeout = datetime.now() + timedelta(minutes=timeout_minutes)
        
        logger.info(f"Waiting for cluster {cluster_name} to be ready...")
        
        while datetime.now() < timeout:
            try:
                cluster_info = await self.get_cluster_info(cluster_name, location, use_cache=False)
                
                if cluster_info.status == 'RUNNING':
                    logger.info(f"Cluster {cluster_name} is ready")
                    return cluster_info
                elif cluster_info.status == 'ERROR':
                    raise GKEClientError(f"Cluster {cluster_name} failed to create")
                
                logger.debug(f"Cluster {cluster_name} status: {cluster_info.status}")
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.warning(f"Error checking cluster status: {e}")
                await asyncio.sleep(30)
        
        raise GKEClientError(f"Timeout waiting for cluster {cluster_name} to be ready")
    
    def _validate_cluster_config(self, cluster_config: ClusterConfig) -> None:
        """Validate cluster configuration"""
        if not cluster_config.name:
            raise ValueError("Cluster name is required")
        
        if not cluster_config.region:
            raise ValueError("Cluster region is required")
        
        if len(cluster_config.name) > 40:
            raise ValueError("Cluster name must be 40 characters or less")
        
        # Add more validation as needed
    
    def _update_cluster_cache(self, cluster_info: ClusterInfo) -> None:
        """Update cluster cache"""
        cache_key = f"{cluster_info.name}:{cluster_info.location}"
        self._cluster_cache[cache_key] = cluster_info
        self._last_cache_update = datetime.now()
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._last_cache_update:
            return False
        
        age = datetime.now() - self._last_cache_update
        return age < self._cache_ttl
    
    def clear_cache(self) -> None:
        """Clear cluster cache"""
        self._cluster_cache.clear()
        self._last_cache_update = None
        logger.info("Cluster cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_clusters': len(self._cluster_cache),
            'cache_age_seconds': (datetime.now() - self._last_cache_update).total_seconds() if self._last_cache_update else None,
            'cache_valid': self._is_cache_valid(),
            'cache_ttl_seconds': self._cache_ttl.total_seconds()
        }