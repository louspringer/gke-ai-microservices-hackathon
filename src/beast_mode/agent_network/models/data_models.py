"""
Beast Mode Agent Network Data Models

Core data structures for agent network coordination and management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class AgentStatus(Enum):
    """Status of an individual agent in the network."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class IntegrationStatus(Enum):
    """Status of system integration with the agent network."""
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class CoordinationStatus(Enum):
    """Overall coordination status of the agent network."""
    OPTIMAL = "optimal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class ResourceUsage:
    """Resource usage metrics for an agent."""
    cpu_percent: float
    memory_mb: float
    network_kb_per_sec: float
    disk_io_kb_per_sec: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetric:
    """Performance metric for an agent or system."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """Information about an individual agent in the network."""
    agent_id: str
    system_type: str  # consensus, orchestration, dag
    capabilities: List[str]
    current_status: AgentStatus
    performance_history: List[PerformanceMetric] = field(default_factory=list)
    resource_usage: Optional[ResourceUsage] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemIntegration:
    """Integration status and metrics for a Beast Mode system."""
    system_name: str
    integration_status: IntegrationStatus
    active_agents: List[str] = field(default_factory=list)
    coordination_overhead: float = 0.0
    success_rate: float = 1.0
    last_health_check: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkPerformanceMetrics:
    """Performance metrics for the entire agent network."""
    total_agents: int = 0
    active_agents: int = 0
    average_coordination_overhead: float = 0.0
    network_efficiency: float = 0.0
    success_rate: float = 1.0
    uptime_percentage: float = 100.0
    last_updated: datetime = field(default_factory=datetime.now)
    system_metrics: Dict[str, PerformanceMetric] = field(default_factory=dict)


@dataclass
class IntelligenceInsights:
    """Intelligence and learning insights from the network."""
    learned_patterns: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    predicted_performance: Dict[str, float] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    last_learning_cycle: datetime = field(default_factory=datetime.now)
    improvement_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AgentNetworkState:
    """Complete state of the Beast Mode Agent Network."""
    active_agents: Dict[str, AgentInfo] = field(default_factory=dict)
    system_integrations: Dict[str, SystemIntegration] = field(default_factory=dict)
    performance_metrics: NetworkPerformanceMetrics = field(default_factory=NetworkPerformanceMetrics)
    coordination_status: CoordinationStatus = CoordinationStatus.OPTIMAL
    intelligence_insights: IntelligenceInsights = field(default_factory=IntelligenceInsights)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now()
    
    def get_agents_by_system(self, system_type: str) -> List[AgentInfo]:
        """Get all agents of a specific system type."""
        return [agent for agent in self.active_agents.values() 
                if agent.system_type == system_type]
    
    def get_agents_by_status(self, status: AgentStatus) -> List[AgentInfo]:
        """Get all agents with a specific status."""
        return [agent for agent in self.active_agents.values() 
                if agent.current_status == status]
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health across all integrations."""
        return {
            'total_systems': len(self.system_integrations),
            'connected_systems': len([s for s in self.system_integrations.values() 
                                    if s.integration_status == IntegrationStatus.CONNECTED]),
            'total_agents': len(self.active_agents),
            'active_agents': len(self.get_agents_by_status(AgentStatus.ACTIVE)),
            'coordination_status': self.coordination_status.value,
            'network_efficiency': self.performance_metrics.network_efficiency,
            'uptime_percentage': self.performance_metrics.uptime_percentage
        }