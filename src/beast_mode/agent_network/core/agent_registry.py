"""
Beast Mode Agent Registry

Unified registry and discovery service for all active agents across Beast Mode systems.
Provides agent registration, discovery, lifecycle management, and performance tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict, replace

from ..models.data_models import (
    AgentInfo,
    AgentStatus,
    PerformanceMetric,
    ResourceUsage
)
from ...core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator


class AgentRegistry(ReflectiveModule):
    """
    Unified registry and discovery service for all active agents.
    
    Manages agent registration, discovery, lifecycle, and performance tracking
    across Multi-Agent Consensus Engine, Multi-Instance Kiro Orchestration,
    and Beast Mode Framework DAG agents.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Agent Registry."""
        super().__init__()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Agent storage
        self.agents: Dict[str, AgentInfo] = {}
        
        # Registry settings
        self.agent_timeout_seconds = self.config.get('agent_timeout_seconds', 300)  # 5 minutes
        self.performance_history_limit = self.config.get('performance_history_limit', 100)
        self.cleanup_interval_seconds = self.config.get('cleanup_interval_seconds', 60)
        
        # Capability indexing for fast discovery
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self.system_index: Dict[str, Set[str]] = {}  # system_type -> set of agent_ids
        self.status_index: Dict[AgentStatus, Set[str]] = {
            status: set() for status in AgentStatus
        }
        
        # Registry state
        self._registry_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        self.logger.info("AgentRegistry initialized with systematic indexing")
    
    async def start(self) -> None:
        """Start the agent registry and begin cleanup monitoring."""
        if self._is_running:
            self.logger.warning("AgentRegistry already running")
            return
        
        self._is_running = True
        
        # Start cleanup monitoring
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("AgentRegistry started successfully")
    
    async def stop(self) -> None:
        """Stop the agent registry and cleanup resources."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel cleanup monitoring
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("AgentRegistry stopped")
    
    async def register_agent(
        self, 
        agent_id: str,
        system_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new agent in the registry.
        
        Args:
            agent_id: Unique identifier for the agent
            system_type: Type of system (consensus, orchestration, dag)
            capabilities: List of capabilities the agent provides
            metadata: Additional metadata about the agent
            
        Returns:
            True if registration successful, False otherwise
        """
        async with self._registry_lock:
            try:
                # Check if agent already exists
                if agent_id in self.agents:
                    self.logger.warning(f"Agent {agent_id} already registered, updating")
                    return await self._update_existing_agent(
                        agent_id, system_type, capabilities, metadata
                    )
                
                # Create new agent info
                agent_info = AgentInfo(
                    agent_id=agent_id,
                    system_type=system_type,
                    capabilities=capabilities,
                    current_status=AgentStatus.IDLE,
                    metadata=metadata or {}
                )
                
                # Add to main registry
                self.agents[agent_id] = agent_info
                
                # Update indexes
                await self._update_indexes_for_agent(agent_info, is_new=True)
                
                self.logger.info(
                    f"Agent registered: {agent_id} ({system_type}) with capabilities: {capabilities}"
                )
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register agent {agent_id}: {e}")
                return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            True if unregistration successful, False otherwise
        """
        async with self._registry_lock:
            try:
                if agent_id not in self.agents:
                    self.logger.warning(f"Agent {agent_id} not found for unregistration")
                    return False
                
                agent_info = self.agents[agent_id]
                
                # Remove from indexes
                await self._remove_from_indexes(agent_info)
                
                # Remove from main registry
                del self.agents[agent_id]
                
                self.logger.info(f"Agent unregistered: {agent_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister agent {agent_id}: {e}")
                return False
    
    async def discover_agents(
        self,
        capabilities: Optional[List[str]] = None,
        system_type: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        limit: Optional[int] = None
    ) -> List[AgentInfo]:
        """
        Find available agents by capability, system type, and status.
        
        Args:
            capabilities: Required capabilities (all must be present)
            system_type: Filter by system type
            status: Filter by agent status
            limit: Maximum number of agents to return
            
        Returns:
            List of matching agent information
        """
        try:
            # Start with all agents
            candidate_ids = set(self.agents.keys())
            
            # Filter by capabilities
            if capabilities:
                for capability in capabilities:
                    if capability in self.capability_index:
                        candidate_ids &= self.capability_index[capability]
                    else:
                        # No agents have this capability
                        return []
            
            # Filter by system type
            if system_type and system_type in self.system_index:
                candidate_ids &= self.system_index[system_type]
            elif system_type:
                # No agents of this system type
                return []
            
            # Filter by status
            if status and status in self.status_index:
                candidate_ids &= self.status_index[status]
            elif status:
                # No agents with this status
                return []
            
            # Get agent info for candidates
            matching_agents = [
                self.agents[agent_id] for agent_id in candidate_ids
                if agent_id in self.agents
            ]
            
            # Sort by performance score (best first)
            matching_agents.sort(
                key=lambda agent: self._calculate_agent_score(agent),
                reverse=True
            )
            
            # Apply limit
            if limit:
                matching_agents = matching_agents[:limit]
            
            self.logger.debug(
                f"Agent discovery found {len(matching_agents)} agents "
                f"(capabilities: {capabilities}, system: {system_type}, status: {status})"
            )
            
            return matching_agents
            
        except Exception as e:
            self.logger.error(f"Agent discovery failed: {e}")
            return []
    
    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update the status of an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            status: New status for the agent
            
        Returns:
            True if update successful, False otherwise
        """
        async with self._registry_lock:
            try:
                if agent_id not in self.agents:
                    self.logger.warning(f"Agent {agent_id} not found for status update")
                    return False
                
                agent_info = self.agents[agent_id]
                old_status = agent_info.current_status
                
                # Update status
                agent_info.current_status = status
                agent_info.last_seen = datetime.now()
                
                # Update status index
                if agent_id in self.status_index[old_status]:
                    self.status_index[old_status].remove(agent_id)
                self.status_index[status].add(agent_id)
                
                self.logger.debug(f"Agent {agent_id} status updated: {old_status.value} -> {status.value}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to update agent {agent_id} status: {e}")
                return False
    
    async def track_agent_performance(
        self,
        agent_id: str,
        performance_metric: PerformanceMetric
    ) -> bool:
        """
        Record a performance metric for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            performance_metric: Performance metric to record
            
        Returns:
            True if tracking successful, False otherwise
        """
        async with self._registry_lock:
            try:
                if agent_id not in self.agents:
                    self.logger.warning(f"Agent {agent_id} not found for performance tracking")
                    return False
                
                agent_info = self.agents[agent_id]
                
                # Add performance metric
                agent_info.performance_history.append(performance_metric)
                
                # Limit history size
                if len(agent_info.performance_history) > self.performance_history_limit:
                    agent_info.performance_history = agent_info.performance_history[-self.performance_history_limit:]
                
                # Update last seen
                agent_info.last_seen = datetime.now()
                
                self.logger.debug(
                    f"Performance metric recorded for agent {agent_id}: "
                    f"{performance_metric.metric_name}={performance_metric.value}"
                )
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to track performance for agent {agent_id}: {e}")
                return False
    
    async def update_agent_resources(
        self,
        agent_id: str,
        resource_usage: ResourceUsage
    ) -> bool:
        """
        Update resource usage information for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            resource_usage: Current resource usage metrics
            
        Returns:
            True if update successful, False otherwise
        """
        async with self._registry_lock:
            try:
                if agent_id not in self.agents:
                    self.logger.warning(f"Agent {agent_id} not found for resource update")
                    return False
                
                agent_info = self.agents[agent_id]
                agent_info.resource_usage = resource_usage
                agent_info.last_seen = datetime.now()
                
                self.logger.debug(f"Resource usage updated for agent {agent_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to update resources for agent {agent_id}: {e}")
                return False
    
    async def manage_agent_lifecycle(self, agent_id: str, action: str) -> bool:
        """
        Coordinate agent creation, execution, and termination.
        
        Args:
            agent_id: Unique identifier for the agent
            action: Lifecycle action (start, pause, resume, stop)
            
        Returns:
            True if lifecycle management successful, False otherwise
        """
        try:
            if agent_id not in self.agents:
                self.logger.warning(f"Agent {agent_id} not found for lifecycle management")
                return False
            
            agent_info = self.agents[agent_id]
            
            # Handle different lifecycle actions
            if action == 'start':
                await self.update_agent_status(agent_id, AgentStatus.ACTIVE)
            elif action == 'pause':
                await self.update_agent_status(agent_id, AgentStatus.IDLE)
            elif action == 'resume':
                await self.update_agent_status(agent_id, AgentStatus.ACTIVE)
            elif action == 'stop':
                await self.update_agent_status(agent_id, AgentStatus.OFFLINE)
            else:
                self.logger.warning(f"Unknown lifecycle action: {action}")
                return False
            
            self.logger.info(f"Agent {agent_id} lifecycle action completed: {action}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to manage lifecycle for agent {agent_id}: {e}")
            return False
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, AgentInfo]:
        """Get information about all registered agents."""
        return self.agents.copy()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the agent registry."""
        stats = {
            'total_agents': len(self.agents),
            'agents_by_status': {
                status.value: len(agent_ids) 
                for status, agent_ids in self.status_index.items()
            },
            'agents_by_system': {
                system: len(agent_ids)
                for system, agent_ids in self.system_index.items()
            },
            'total_capabilities': len(self.capability_index),
            'registry_uptime_seconds': (
                (datetime.now() - self.agents[list(self.agents.keys())[0]].created_at).total_seconds()
                if self.agents else 0
            )
        }
        
        return stats
    
    async def get_agents_by_capability_match(
        self,
        required_capabilities: List[str],
        preferred_capabilities: Optional[List[str]] = None
    ) -> List[AgentInfo]:
        """
        Get agents with capability-based matching and scoring.
        
        Args:
            required_capabilities: Capabilities that must be present
            preferred_capabilities: Capabilities that are preferred but not required
            
        Returns:
            List of agents sorted by capability match score
        """
        try:
            # Find agents with all required capabilities
            agents_with_required = await self.discover_agents(capabilities=required_capabilities)
            
            if not preferred_capabilities:
                return agents_with_required
            
            # Score agents based on preferred capabilities
            scored_agents = []
            for agent in agents_with_required:
                score = self._calculate_capability_match_score(
                    agent.capabilities, required_capabilities, preferred_capabilities
                )
                scored_agents.append((agent, score))
            
            # Sort by score (highest first)
            scored_agents.sort(key=lambda x: x[1], reverse=True)
            
            return [agent for agent, score in scored_agents]
            
        except Exception as e:
            self.logger.error(f"Capability-based agent matching failed: {e}")
            return []
    
    # Private methods for internal registry operations
    
    async def _cleanup_loop(self) -> None:
        """Continuous cleanup loop for stale agents."""
        while self._is_running:
            try:
                await self._cleanup_stale_agents()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Agent cleanup error: {e}")
                await asyncio.sleep(self.cleanup_interval_seconds)
    
    async def _cleanup_stale_agents(self) -> None:
        """Remove agents that haven't been seen for too long."""
        async with self._registry_lock:
            current_time = datetime.now()
            stale_agents = []
            
            for agent_id, agent_info in self.agents.items():
                time_since_last_seen = (current_time - agent_info.last_seen).total_seconds()
                if time_since_last_seen > self.agent_timeout_seconds:
                    stale_agents.append(agent_id)
            
            # Remove stale agents
            for agent_id in stale_agents:
                await self._remove_stale_agent(agent_id)
            
            if stale_agents:
                self.logger.info(f"Cleaned up {len(stale_agents)} stale agents")
    
    async def _remove_stale_agent(self, agent_id: str) -> None:
        """Remove a stale agent from the registry."""
        if agent_id in self.agents:
            agent_info = self.agents[agent_id]
            await self._remove_from_indexes(agent_info)
            del self.agents[agent_id]
            self.logger.debug(f"Removed stale agent: {agent_id}")
    
    async def _update_existing_agent(
        self,
        agent_id: str,
        system_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Update an existing agent's information."""
        agent_info = self.agents[agent_id]
        
        # Remove from old indexes
        await self._remove_from_indexes(agent_info)
        
        # Update agent info
        agent_info.system_type = system_type
        agent_info.capabilities = capabilities
        agent_info.last_seen = datetime.now()
        if metadata:
            agent_info.metadata.update(metadata)
        
        # Update indexes with new information
        await self._update_indexes_for_agent(agent_info, is_new=False)
        
        return True
    
    async def _update_indexes_for_agent(self, agent_info: AgentInfo, is_new: bool) -> None:
        """Update all indexes for an agent."""
        agent_id = agent_info.agent_id
        
        # Update capability index
        for capability in agent_info.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(agent_id)
        
        # Update system index
        if agent_info.system_type not in self.system_index:
            self.system_index[agent_info.system_type] = set()
        self.system_index[agent_info.system_type].add(agent_id)
        
        # Update status index
        self.status_index[agent_info.current_status].add(agent_id)
    
    async def _remove_from_indexes(self, agent_info: AgentInfo) -> None:
        """Remove an agent from all indexes."""
        agent_id = agent_info.agent_id
        
        # Remove from capability index
        for capability in agent_info.capabilities:
            if capability in self.capability_index:
                self.capability_index[capability].discard(agent_id)
                # Clean up empty capability entries
                if not self.capability_index[capability]:
                    del self.capability_index[capability]
        
        # Remove from system index
        if agent_info.system_type in self.system_index:
            self.system_index[agent_info.system_type].discard(agent_id)
            # Clean up empty system entries
            if not self.system_index[agent_info.system_type]:
                del self.system_index[agent_info.system_type]
        
        # Remove from status index
        self.status_index[agent_info.current_status].discard(agent_id)
    
    def _calculate_agent_score(self, agent_info: AgentInfo) -> float:
        """Calculate a performance score for an agent."""
        base_score = 0.5
        
        # Factor in recent performance
        if agent_info.performance_history:
            recent_metrics = agent_info.performance_history[-10:]  # Last 10 metrics
            avg_performance = sum(metric.value for metric in recent_metrics) / len(recent_metrics)
            base_score = (base_score + avg_performance) / 2
        
        # Factor in status
        status_multipliers = {
            AgentStatus.ACTIVE: 1.0,
            AgentStatus.IDLE: 0.8,
            AgentStatus.BUSY: 0.6,
            AgentStatus.ERROR: 0.2,
            AgentStatus.OFFLINE: 0.0
        }
        
        base_score *= status_multipliers.get(agent_info.current_status, 0.5)
        
        # Factor in resource usage if available
        if agent_info.resource_usage:
            # Lower CPU usage is better for availability
            cpu_factor = max(0.1, 1.0 - (agent_info.resource_usage.cpu_percent / 100.0))
            base_score *= cpu_factor
        
        return min(1.0, max(0.0, base_score))
    
    def _calculate_capability_match_score(
        self,
        agent_capabilities: List[str],
        required_capabilities: List[str],
        preferred_capabilities: List[str]
    ) -> float:
        """Calculate how well an agent's capabilities match requirements."""
        # Base score for having all required capabilities
        score = 1.0
        
        # Bonus for preferred capabilities
        preferred_matches = len(set(agent_capabilities) & set(preferred_capabilities))
        preferred_bonus = preferred_matches / len(preferred_capabilities) if preferred_capabilities else 0
        
        # Bonus for additional capabilities
        total_capabilities = len(agent_capabilities)
        capability_bonus = min(0.2, total_capabilities * 0.05)  # Max 20% bonus
        
        return score + preferred_bonus + capability_bonus
    
    # ReflectiveModule implementation
    
    def get_module_status(self) -> ModuleStatus:
        """Get the current operational status of the agent registry."""
        if not self._is_running:
            return ModuleStatus.SHUTDOWN
        
        # Check registry health based on agent activity and errors
        total_agents = len(self.agents)
        active_agents = len(self.status_index.get(AgentStatus.ACTIVE, set()))
        error_agents = len(self.status_index.get(AgentStatus.ERROR, set()))
        
        if total_agents == 0:
            return ModuleStatus.HEALTHY  # Empty registry is still healthy
        
        error_rate = error_agents / total_agents if total_agents > 0 else 0
        active_rate = active_agents / total_agents if total_agents > 0 else 0
        
        if error_rate > 0.5:  # More than 50% agents in error
            return ModuleStatus.UNHEALTHY
        elif error_rate > 0.2 or active_rate < 0.3:  # High error rate or low activity
            return ModuleStatus.DEGRADED
        else:
            return ModuleStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """Check if the agent registry is currently healthy."""
        return (self._is_running and 
                self.get_module_status() in [ModuleStatus.HEALTHY, ModuleStatus.DEGRADED])
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get detailed health indicators for the agent registry."""
        indicators = []
        
        # Registry running status
        indicators.append(HealthIndicator(
            name="registry_running",
            status="healthy" if self._is_running else "unhealthy",
            message="Agent registry is running" if self._is_running else "Agent registry is stopped"
        ))
        
        # Agent counts by status
        total_agents = len(self.agents)
        status_counts = {
            status.value: len(agent_ids) 
            for status, agent_ids in self.status_index.items()
        }
        
        indicators.append(HealthIndicator(
            name="agent_population",
            status="healthy" if total_agents > 0 else "degraded",
            message=f"Total registered agents: {total_agents}",
            details={"total": total_agents, "by_status": status_counts}
        ))
        
        # Active agents ratio
        active_agents = len(self.status_index.get(AgentStatus.ACTIVE, set()))
        active_ratio = active_agents / total_agents if total_agents > 0 else 0
        
        indicators.append(HealthIndicator(
            name="agent_activity",
            status="healthy" if active_ratio >= 0.3 else "degraded",
            message=f"Active agents: {active_agents}/{total_agents} ({active_ratio:.1%})",
            details={"active": active_agents, "total": total_agents, "ratio": active_ratio}
        ))
        
        # Error agents ratio
        error_agents = len(self.status_index.get(AgentStatus.ERROR, set()))
        error_ratio = error_agents / total_agents if total_agents > 0 else 0
        
        indicators.append(HealthIndicator(
            name="agent_errors",
            status="healthy" if error_ratio <= 0.2 else "unhealthy",
            message=f"Error agents: {error_agents}/{total_agents} ({error_ratio:.1%})",
            details={"error": error_agents, "total": total_agents, "ratio": error_ratio}
        ))
        
        # System type distribution
        system_counts = {
            system: len(agent_ids)
            for system, agent_ids in self.system_index.items()
        }
        
        indicators.append(HealthIndicator(
            name="system_distribution",
            status="healthy" if len(system_counts) > 0 else "degraded",
            message=f"Agent systems: {len(system_counts)} types",
            details={"systems": system_counts}
        ))
        
        # Capability coverage
        total_capabilities = len(self.capability_index)
        
        indicators.append(HealthIndicator(
            name="capability_coverage",
            status="healthy" if total_capabilities > 0 else "degraded",
            message=f"Available capabilities: {total_capabilities}",
            details={"total_capabilities": total_capabilities}
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information about the agent registry."""
        stats = self.get_registry_stats()
        
        return {
            "module_type": "AgentRegistry",
            "is_running": self._is_running,
            "configuration": {
                "agent_timeout_seconds": self.agent_timeout_seconds,
                "performance_history_limit": self.performance_history_limit,
                "cleanup_interval_seconds": self.cleanup_interval_seconds
            },
            "registry_statistics": stats,
            "index_statistics": {
                "capability_index_size": len(self.capability_index),
                "system_index_size": len(self.system_index),
                "status_index_entries": {
                    status.value: len(agent_ids)
                    for status, agent_ids in self.status_index.items()
                }
            },
            "agent_details": {
                agent_id: {
                    "system_type": agent.system_type,
                    "capabilities": agent.capabilities,
                    "status": agent.current_status.value,
                    "performance_history_count": len(agent.performance_history),
                    "last_seen": agent.last_seen.isoformat(),
                    "uptime_seconds": (datetime.now() - agent.created_at).total_seconds()
                }
                for agent_id, agent in self.agents.items()
            },
            "capabilities": [
                "agent_registration",
                "agent_discovery",
                "performance_tracking",
                "lifecycle_management",
                "capability_matching"
            ],
            "uptime_seconds": self.get_uptime()
        }