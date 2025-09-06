"""Cluster lifecycle management utilities."""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from .kind_manager import KindManager, ClusterStatus
from .registry import LocalRegistryManager, RegistryIntegration
from ..config.models import GKELocalConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ClusterState(Enum):
    """Possible cluster states."""
    NOT_EXISTS = "not_exists"
    CREATING = "creating"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DELETING = "deleting"
    ERROR = "error"


@dataclass
class ClusterEvent:
    """Represents a cluster lifecycle event."""
    cluster_name: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]


class ClusterLifecycleManager:
    """Manages the complete lifecycle of Kind clusters."""
    
    def __init__(self, config: GKELocalConfig):
        """Initialize lifecycle manager.
        
        Args:
            config: GKE Local configuration
        """
        self.config = config
        self.kind_manager = KindManager(config)
        self.registry_manager = LocalRegistryManager(config)
        self.registry_integration = RegistryIntegration(self.registry_manager)
        self.cluster_name = config.cluster.name
        self._state = ClusterState.NOT_EXISTS
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        
    @property
    def state(self) -> ClusterState:
        """Get current cluster state."""
        return self._state
    
    async def initialize(self) -> bool:
        """Initialize the cluster lifecycle manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Initializing cluster lifecycle manager")
        
        try:
            # Check current cluster state
            await self._update_state()
            
            # Start monitoring if cluster exists
            if self._state in [ClusterState.READY, ClusterState.ERROR]:
                await self.start_monitoring()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize lifecycle manager: {e}")
            return False
    
    async def create_and_start(self) -> bool:
        """Create and start the cluster.
        
        Returns:
            True if cluster is ready, False otherwise
        """
        logger.info(f"Creating and starting cluster: {self.cluster_name}")
        
        try:
            self._state = ClusterState.CREATING
            await self._emit_event("cluster_creating", {})
            
            # Start registry if not running
            await self._ensure_registry_running()
            
            # Create cluster
            success = await self.kind_manager.create_cluster()
            
            if success:
                # Wait for cluster to be ready
                await self._wait_for_ready()
                
                if self._state == ClusterState.READY:
                    # Connect registry to cluster
                    await self._connect_registry_to_cluster()
                    
                    await self._emit_event("cluster_ready", {})
                    await self.start_monitoring()
                    return True
                else:
                    self._state = ClusterState.ERROR
                    await self._emit_event("cluster_error", {"error": "Cluster not ready after creation"})
                    return False
            else:
                self._state = ClusterState.ERROR
                await self._emit_event("cluster_error", {"error": "Failed to create cluster"})
                return False
                
        except Exception as e:
            logger.error(f"Error creating cluster: {e}")
            self._state = ClusterState.ERROR
            await self._emit_event("cluster_error", {"error": str(e)})
            return False
    
    async def stop_and_cleanup(self) -> bool:
        """Stop and clean up the cluster.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        logger.info(f"Stopping and cleaning up cluster: {self.cluster_name}")
        
        try:
            # Stop monitoring
            await self.stop_monitoring()
            
            self._state = ClusterState.DELETING
            await self._emit_event("cluster_deleting", {})
            
            # Delete cluster (Kind doesn't support stopping)
            success = await self.kind_manager.delete_cluster()
            
            if success:
                self._state = ClusterState.NOT_EXISTS
                await self._emit_event("cluster_deleted", {})
                return True
            else:
                self._state = ClusterState.ERROR
                await self._emit_event("cluster_error", {"error": "Failed to delete cluster"})
                return False
                
        except Exception as e:
            logger.error(f"Error stopping cluster: {e}")
            self._state = ClusterState.ERROR
            await self._emit_event("cluster_error", {"error": str(e)})
            return False
    
    async def reset(self) -> bool:
        """Reset the cluster by recreating it.
        
        Returns:
            True if reset successful, False otherwise
        """
        logger.info(f"Resetting cluster: {self.cluster_name}")
        
        try:
            # Stop and cleanup
            await self.stop_and_cleanup()
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Create and start again
            return await self.create_and_start()
            
        except Exception as e:
            logger.error(f"Error resetting cluster: {e}")
            return False
    
    async def get_status(self) -> ClusterStatus:
        """Get detailed cluster status.
        
        Returns:
            Current cluster status
        """
        return await self.kind_manager.get_cluster_status()
    
    async def wait_for_ready(self, timeout: int = 300) -> bool:
        """Wait for cluster to be ready.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if cluster becomes ready, False if timeout
        """
        logger.info(f"Waiting for cluster to be ready (timeout: {timeout}s)")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                logger.error("Timeout waiting for cluster to be ready")
                return False
            
            status = await self.get_status()
            if status.is_ready:
                self._state = ClusterState.READY
                logger.info("Cluster is ready")
                return True
            
            await asyncio.sleep(5)
    
    async def start_monitoring(self) -> None:
        """Start monitoring cluster health."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        logger.info("Starting cluster monitoring")
        self._monitoring_task = asyncio.create_task(self._monitor_cluster())
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring cluster health."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.info("Stopping cluster monitoring")
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add an event handler for cluster events.
        
        Args:
            event_type: Type of event to handle
            handler: Callback function to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove an event handler.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def _update_state(self) -> None:
        """Update the current cluster state."""
        try:
            status = await self.get_status()
            
            if not status.exists:
                self._state = ClusterState.NOT_EXISTS
            elif status.is_ready:
                self._state = ClusterState.READY
            else:
                self._state = ClusterState.ERROR
                
        except Exception as e:
            logger.error(f"Error updating cluster state: {e}")
            self._state = ClusterState.ERROR
    
    async def _wait_for_ready(self) -> None:
        """Wait for cluster to be ready after creation."""
        await self.wait_for_ready()
    
    async def _monitor_cluster(self) -> None:
        """Monitor cluster health continuously."""
        logger.info("Starting cluster health monitoring")
        
        try:
            while True:
                previous_state = self._state
                await self._update_state()
                
                # Emit event if state changed
                if self._state != previous_state:
                    await self._emit_event("state_changed", {
                        "previous_state": previous_state.value,
                        "new_state": self._state.value
                    })
                
                # Check for specific issues
                if self._state == ClusterState.READY:
                    await self._check_cluster_health()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Cluster monitoring stopped")
            raise
        except Exception as e:
            logger.error(f"Error in cluster monitoring: {e}")
            self._state = ClusterState.ERROR
            await self._emit_event("monitoring_error", {"error": str(e)})
    
    async def _check_cluster_health(self) -> None:
        """Check detailed cluster health."""
        try:
            status = await self.get_status()
            
            # Check node health
            unhealthy_nodes = []
            for node in status.nodes:
                node_name = node.get('metadata', {}).get('name', 'unknown')
                conditions = node.get('status', {}).get('conditions', [])
                
                ready_condition = next(
                    (c for c in conditions if c.get('type') == 'Ready'),
                    None
                )
                
                if not ready_condition or ready_condition.get('status') != 'True':
                    unhealthy_nodes.append(node_name)
            
            if unhealthy_nodes:
                await self._emit_event("unhealthy_nodes", {
                    "nodes": unhealthy_nodes
                })
            
        except Exception as e:
            logger.error(f"Error checking cluster health: {e}")
    
    async def _ensure_registry_running(self) -> None:
        """Ensure the local registry is running."""
        try:
            registry_status = await self.registry_manager.get_registry_status()
            
            if not registry_status.is_accessible:
                logger.info("Starting local registry for cluster")
                await self.registry_manager.start_registry()
            else:
                logger.info("Local registry is already running")
                
        except Exception as e:
            logger.warning(f"Could not ensure registry is running: {e}")
    
    async def _connect_registry_to_cluster(self) -> None:
        """Connect the local registry to the cluster."""
        try:
            logger.info("Connecting registry to cluster")
            success = await self.registry_integration.setup_cluster_registry_connection(self.cluster_name)
            
            if success:
                logger.info("Successfully connected registry to cluster")
            else:
                logger.warning("Failed to connect registry to cluster")
                
        except Exception as e:
            logger.warning(f"Error connecting registry to cluster: {e}")
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a cluster event to registered handlers.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        event = ClusterEvent(
            cluster_name=self.cluster_name,
            event_type=event_type,
            timestamp=asyncio.get_event_loop().time(),
            data=data
        )
        
        logger.debug(f"Emitting event: {event_type} for cluster {self.cluster_name}")
        
        # Call registered handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")


class ClusterOrchestrator:
    """Orchestrates multiple cluster lifecycle managers."""
    
    def __init__(self):
        """Initialize cluster orchestrator."""
        self.clusters: Dict[str, ClusterLifecycleManager] = {}
        self.default_cluster: Optional[str] = None
    
    def add_cluster(self, config: GKELocalConfig) -> ClusterLifecycleManager:
        """Add a cluster to the orchestrator.
        
        Args:
            config: Cluster configuration
            
        Returns:
            Cluster lifecycle manager
        """
        cluster_name = config.cluster.name
        manager = ClusterLifecycleManager(config)
        
        self.clusters[cluster_name] = manager
        
        if self.default_cluster is None:
            self.default_cluster = cluster_name
        
        return manager
    
    def get_cluster(self, name: Optional[str] = None) -> Optional[ClusterLifecycleManager]:
        """Get a cluster manager by name.
        
        Args:
            name: Cluster name, or None for default cluster
            
        Returns:
            Cluster lifecycle manager, or None if not found
        """
        if name is None:
            name = self.default_cluster
        
        return self.clusters.get(name)
    
    def list_clusters(self) -> List[str]:
        """List all managed clusters.
        
        Returns:
            List of cluster names
        """
        return list(self.clusters.keys())
    
    async def start_all(self) -> Dict[str, bool]:
        """Start all managed clusters.
        
        Returns:
            Dictionary mapping cluster names to success status
        """
        results = {}
        
        for name, manager in self.clusters.items():
            logger.info(f"Starting cluster: {name}")
            results[name] = await manager.create_and_start()
        
        return results
    
    async def stop_all(self) -> Dict[str, bool]:
        """Stop all managed clusters.
        
        Returns:
            Dictionary mapping cluster names to success status
        """
        results = {}
        
        for name, manager in self.clusters.items():
            logger.info(f"Stopping cluster: {name}")
            results[name] = await manager.stop_and_cleanup()
        
        return results
    
    async def get_all_status(self) -> Dict[str, ClusterStatus]:
        """Get status of all managed clusters.
        
        Returns:
            Dictionary mapping cluster names to their status
        """
        results = {}
        
        for name, manager in self.clusters.items():
            results[name] = await manager.get_status()
        
        return results