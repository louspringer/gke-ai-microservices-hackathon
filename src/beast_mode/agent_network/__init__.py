"""
Beast Mode Agent Network

Unified coordination layer for all multi-agent operations across the Beast Mode ecosystem.
Integrates multi-agent consensus, distributed orchestration, and swarm coordination capabilities.
"""

from .core.network_coordinator import NetworkCoordinator
from .core.agent_registry import AgentRegistry
from .integrations.consensus_orchestrator import ConsensusOrchestrator
from .integrations.swarm_manager import SwarmManager, DeploymentTarget
from .integrations.dag_agent_coordinator import DAGAgentCoordinator
from .models.data_models import (
    AgentNetworkState,
    AgentInfo,
    SystemIntegration,
    NetworkPerformanceMetrics,
    IntelligenceInsights,
    AgentStatus,
    IntegrationStatus,
    CoordinationStatus,
    ResourceUsage,
    PerformanceMetric
)

__all__ = [
    # Core components
    'NetworkCoordinator',
    'AgentRegistry',
    
    # Integration layers
    'ConsensusOrchestrator',
    'SwarmManager',
    'DAGAgentCoordinator',
    'DeploymentTarget',
    
    # Data models
    'AgentNetworkState',
    'AgentInfo',
    'SystemIntegration',
    'NetworkPerformanceMetrics',
    'IntelligenceInsights',
    'AgentStatus',
    'IntegrationStatus',
    'CoordinationStatus',
    'ResourceUsage',
    'PerformanceMetric'
]