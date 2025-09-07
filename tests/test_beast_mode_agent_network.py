"""
Tests for Beast Mode Agent Network

Comprehensive test suite for the agent network coordination and registry systems.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.beast_mode.agent_network.core.network_coordinator import NetworkCoordinator
from src.beast_mode.agent_network.core.agent_registry import AgentRegistry
from src.beast_mode.agent_network.models.data_models import (
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


class TestAgentNetworkDataModels:
    """Test the agent network data models."""
    
    def test_agent_info_creation(self):
        """Test AgentInfo creation and basic properties."""
        agent_info = AgentInfo(
            agent_id="test-agent-1",
            system_type="consensus",
            capabilities=["voting", "conflict_resolution"],
            current_status=AgentStatus.ACTIVE
        )
        
        assert agent_info.agent_id == "test-agent-1"
        assert agent_info.system_type == "consensus"
        assert agent_info.capabilities == ["voting", "conflict_resolution"]
        assert agent_info.current_status == AgentStatus.ACTIVE
        assert isinstance(agent_info.created_at, datetime)
        assert isinstance(agent_info.last_seen, datetime)
    
    def test_agent_network_state_methods(self):
        """Test AgentNetworkState utility methods."""
        state = AgentNetworkState()
        
        # Add test agents
        agent1 = AgentInfo(
            agent_id="agent1",
            system_type="consensus",
            capabilities=["voting"],
            current_status=AgentStatus.ACTIVE
        )
        agent2 = AgentInfo(
            agent_id="agent2",
            system_type="orchestration",
            capabilities=["task_distribution"],
            current_status=AgentStatus.IDLE
        )
        
        state.active_agents["agent1"] = agent1
        state.active_agents["agent2"] = agent2
        
        # Test get_agents_by_system
        consensus_agents = state.get_agents_by_system("consensus")
        assert len(consensus_agents) == 1
        assert consensus_agents[0].agent_id == "agent1"
        
        # Test get_agents_by_status
        active_agents = state.get_agents_by_status(AgentStatus.ACTIVE)
        assert len(active_agents) == 1
        assert active_agents[0].agent_id == "agent1"
        
        # Test health summary
        health_summary = state.get_system_health_summary()
        assert health_summary['total_agents'] == 2
        assert health_summary['active_agents'] == 1
    
    def test_resource_usage_tracking(self):
        """Test ResourceUsage data model."""
        resource_usage = ResourceUsage(
            cpu_percent=45.5,
            memory_mb=512.0,
            network_kb_per_sec=100.0,
            disk_io_kb_per_sec=50.0
        )
        
        assert resource_usage.cpu_percent == 45.5
        assert resource_usage.memory_mb == 512.0
        assert isinstance(resource_usage.timestamp, datetime)
    
    def test_performance_metric_creation(self):
        """Test PerformanceMetric data model."""
        metric = PerformanceMetric(
            metric_name="task_completion_time",
            value=1.5,
            unit="seconds",
            metadata={"task_type": "consensus_voting"}
        )
        
        assert metric.metric_name == "task_completion_time"
        assert metric.value == 1.5
        assert metric.unit == "seconds"
        assert metric.metadata["task_type"] == "consensus_voting"
        assert isinstance(metric.timestamp, datetime)


class TestAgentRegistry:
    """Test the Agent Registry functionality."""
    
    @pytest.fixture
    async def registry(self):
        """Create a test agent registry."""
        registry = AgentRegistry(config={
            'agent_timeout_seconds': 60,
            'cleanup_interval_seconds': 10
        })
        await registry.start()
        yield registry
        await registry.stop()
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, registry):
        """Test agent registration functionality."""
        # Register a new agent
        success = await registry.register_agent(
            agent_id="test-agent-1",
            system_type="consensus",
            capabilities=["voting", "conflict_resolution"],
            metadata={"version": "1.0"}
        )
        
        assert success is True
        
        # Verify agent is registered
        agent_info = registry.get_agent_info("test-agent-1")
        assert agent_info is not None
        assert agent_info.agent_id == "test-agent-1"
        assert agent_info.system_type == "consensus"
        assert agent_info.capabilities == ["voting", "conflict_resolution"]
        assert agent_info.metadata["version"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_agent_discovery(self, registry):
        """Test agent discovery functionality."""
        # Register multiple agents
        await registry.register_agent(
            "agent1", "consensus", ["voting", "analysis"]
        )
        await registry.register_agent(
            "agent2", "orchestration", ["task_distribution", "monitoring"]
        )
        await registry.register_agent(
            "agent3", "consensus", ["voting", "conflict_resolution"]
        )
        
        # Test discovery by capabilities
        voting_agents = await registry.discover_agents(capabilities=["voting"])
        assert len(voting_agents) == 2
        
        # Test discovery by system type
        consensus_agents = await registry.discover_agents(system_type="consensus")
        assert len(consensus_agents) == 2
        
        # Test discovery by status
        idle_agents = await registry.discover_agents(status=AgentStatus.IDLE)
        assert len(idle_agents) == 3  # All agents start as IDLE
        
        # Test combined discovery
        consensus_voting_agents = await registry.discover_agents(
            capabilities=["voting"],
            system_type="consensus"
        )
        assert len(consensus_voting_agents) == 2
    
    @pytest.mark.asyncio
    async def test_agent_status_updates(self, registry):
        """Test agent status update functionality."""
        # Register an agent
        await registry.register_agent("agent1", "consensus", ["voting"])
        
        # Update status
        success = await registry.update_agent_status("agent1", AgentStatus.ACTIVE)
        assert success is True
        
        # Verify status update
        agent_info = registry.get_agent_info("agent1")
        assert agent_info.current_status == AgentStatus.ACTIVE
        
        # Test discovery by new status
        active_agents = await registry.discover_agents(status=AgentStatus.ACTIVE)
        assert len(active_agents) == 1
        assert active_agents[0].agent_id == "agent1"
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, registry):
        """Test agent performance tracking."""
        # Register an agent
        await registry.register_agent("agent1", "consensus", ["voting"])
        
        # Track performance metrics
        metric1 = PerformanceMetric("task_time", 1.5, "seconds")
        metric2 = PerformanceMetric("accuracy", 0.95, "ratio")
        
        success1 = await registry.track_agent_performance("agent1", metric1)
        success2 = await registry.track_agent_performance("agent1", metric2)
        
        assert success1 is True
        assert success2 is True
        
        # Verify metrics are stored
        agent_info = registry.get_agent_info("agent1")
        assert len(agent_info.performance_history) == 2
        assert agent_info.performance_history[0].metric_name == "task_time"
        assert agent_info.performance_history[1].metric_name == "accuracy"
    
    @pytest.mark.asyncio
    async def test_capability_based_matching(self, registry):
        """Test capability-based agent matching."""
        # Register agents with different capabilities
        await registry.register_agent(
            "agent1", "consensus", ["voting", "analysis", "reporting"]
        )
        await registry.register_agent(
            "agent2", "consensus", ["voting", "conflict_resolution"]
        )
        await registry.register_agent(
            "agent3", "orchestration", ["voting", "task_distribution", "monitoring"]
        )
        
        # Test capability matching
        matched_agents = await registry.get_agents_by_capability_match(
            required_capabilities=["voting"],
            preferred_capabilities=["analysis", "reporting"]
        )
        
        assert len(matched_agents) >= 1
        # Agent1 should score highest due to preferred capabilities
        assert matched_agents[0].agent_id == "agent1"
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self, registry):
        """Test agent lifecycle management."""
        # Register an agent
        await registry.register_agent("agent1", "consensus", ["voting"])
        
        # Test lifecycle actions
        success_start = await registry.manage_agent_lifecycle("agent1", "start")
        assert success_start is True
        
        agent_info = registry.get_agent_info("agent1")
        assert agent_info.current_status == AgentStatus.ACTIVE
        
        success_pause = await registry.manage_agent_lifecycle("agent1", "pause")
        assert success_pause is True
        
        agent_info = registry.get_agent_info("agent1")
        assert agent_info.current_status == AgentStatus.IDLE
    
    @pytest.mark.asyncio
    async def test_registry_statistics(self, registry):
        """Test registry statistics functionality."""
        # Register multiple agents
        await registry.register_agent("agent1", "consensus", ["voting"])
        await registry.register_agent("agent2", "orchestration", ["task_distribution"])
        await registry.update_agent_status("agent1", AgentStatus.ACTIVE)
        
        # Get statistics
        stats = registry.get_registry_stats()
        
        assert stats['total_agents'] == 2
        assert stats['agents_by_status'][AgentStatus.ACTIVE.value] == 1
        assert stats['agents_by_status'][AgentStatus.IDLE.value] == 1
        assert stats['agents_by_system']['consensus'] == 1
        assert stats['agents_by_system']['orchestration'] == 1
    
    @pytest.mark.asyncio
    async def test_agent_unregistration(self, registry):
        """Test agent unregistration functionality."""
        # Register an agent
        await registry.register_agent("agent1", "consensus", ["voting"])
        
        # Verify registration
        assert registry.get_agent_info("agent1") is not None
        
        # Unregister agent
        success = await registry.unregister_agent("agent1")
        assert success is True
        
        # Verify unregistration
        assert registry.get_agent_info("agent1") is None
        
        # Verify indexes are cleaned up
        voting_agents = await registry.discover_agents(capabilities=["voting"])
        assert len(voting_agents) == 0


class TestNetworkCoordinator:
    """Test the Network Coordinator functionality."""
    
    @pytest.fixture
    async def coordinator(self):
        """Create a test network coordinator."""
        coordinator = NetworkCoordinator(config={
            'max_coordination_overhead_ms': 100,
            'health_check_interval_seconds': 5
        })
        await coordinator.start()
        yield coordinator
        await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """Test network coordinator initialization."""
        assert coordinator.network_state is not None
        assert coordinator.network_state.coordination_status == CoordinationStatus.OPTIMAL
        assert coordinator._is_running is True
    
    @pytest.mark.asyncio
    async def test_system_integration_registration(self, coordinator):
        """Test system integration registration."""
        # Create mock integration handler
        mock_handler = Mock()
        
        # Register system integration
        coordinator.register_system_integration("consensus", mock_handler)
        
        # Verify registration
        assert coordinator.system_integrations["consensus"] == mock_handler
        assert "consensus" in coordinator.network_state.system_integrations
        assert (coordinator.network_state.system_integrations["consensus"].integration_status 
                == IntegrationStatus.CONNECTED)
    
    @pytest.mark.asyncio
    async def test_multi_system_agent_coordination(self, coordinator):
        """Test multi-system agent coordination."""
        # Setup mock system integrations
        coordinator.register_system_integration("consensus", Mock())
        coordinator.register_system_integration("orchestration", Mock())
        
        # Add mock agents to network state
        agent1 = AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE)
        agent2 = AgentInfo("agent2", "orchestration", ["task_distribution"], AgentStatus.ACTIVE)
        
        coordinator.network_state.active_agents["agent1"] = agent1
        coordinator.network_state.active_agents["agent2"] = agent2
        
        # Update system integrations with active agents
        coordinator.network_state.system_integrations["consensus"].active_agents = ["agent1"]
        coordinator.network_state.system_integrations["orchestration"].active_agents = ["agent2"]
        
        # Test coordination
        task_requirements = {
            "complexity": "medium",
            "capabilities": ["voting", "task_distribution"],
            "resources": {"cpu": 2, "memory": "1GB"}
        }
        
        result = await coordinator.coordinate_multi_system_agents(task_requirements)
        
        assert result["success"] is True
        assert "coordination_plan" in result
        assert "execution_result" in result
        assert "coordination_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_agent_allocation_optimization(self, coordinator):
        """Test agent allocation optimization."""
        # Setup test scenario
        workload_forecast = {
            "expected_tasks": 10,
            "peak_hours": ["09:00", "17:00"],
            "resource_requirements": {"cpu": 4, "memory": "2GB"}
        }
        
        result = await coordinator.optimize_agent_allocation(workload_forecast)
        
        assert result["success"] is True
        assert "allocation_strategy" in result
        assert "allocation_result" in result
    
    @pytest.mark.asyncio
    async def test_cross_system_conflict_resolution(self, coordinator):
        """Test cross-system conflict resolution."""
        # Setup conflict scenario
        conflict_data = {
            "type": "resource_contention",
            "systems": ["consensus", "orchestration"],
            "agents": ["agent1", "agent2"],
            "resource": "cpu_cores"
        }
        
        result = await coordinator.handle_cross_system_conflicts(conflict_data)
        
        assert result["success"] is True
        assert "conflict_classification" in result
        assert "resolution_strategy" in result
        assert "resolution_result" in result
    
    @pytest.mark.asyncio
    async def test_network_health_monitoring(self, coordinator):
        """Test network health monitoring."""
        # Setup system integrations
        coordinator.register_system_integration("consensus", Mock())
        
        # Add test agent
        agent1 = AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE)
        coordinator.network_state.active_agents["agent1"] = agent1
        
        # Monitor health
        health_report = await coordinator.monitor_network_health()
        
        assert "coordination_status" in health_report
        assert "system_health" in health_report
        assert "agent_health" in health_report
        assert "network_metrics" in health_report
        assert "health_summary" in health_report
        assert "timestamp" in health_report
    
    @pytest.mark.asyncio
    async def test_coordination_performance_tracking(self, coordinator):
        """Test coordination performance tracking."""
        # Perform coordination operation
        task_requirements = {"complexity": "low"}
        result = await coordinator.coordinate_multi_system_agents(task_requirements)
        
        # Verify performance tracking
        assert "coordination_time_ms" in result
        coordination_time = result["coordination_time_ms"]
        assert isinstance(coordination_time, float)
        assert coordination_time >= 0
        
        # Check that performance is recorded in network state
        network_metrics = coordinator.network_state.performance_metrics
        assert network_metrics.average_coordination_overhead >= 0
    
    @pytest.mark.asyncio
    async def test_coordination_status_determination(self, coordinator):
        """Test coordination status determination logic."""
        # Test optimal status
        health_report = await coordinator.monitor_network_health()
        assert coordinator.network_state.coordination_status == CoordinationStatus.OPTIMAL
        
        # Simulate degraded performance by setting high overhead
        coordinator.network_state.performance_metrics.average_coordination_overhead = 150  # > 100ms limit
        
        health_report = await coordinator.monitor_network_health()
        # Status should be degraded due to high overhead
        assert coordinator.network_state.coordination_status in [
            CoordinationStatus.DEGRADED, CoordinationStatus.CRITICAL
        ]
    
    def test_network_state_access(self, coordinator):
        """Test network state access methods."""
        network_state = coordinator.get_network_state()
        
        assert isinstance(network_state, AgentNetworkState)
        assert network_state.coordination_status == CoordinationStatus.OPTIMAL
        assert isinstance(network_state.performance_metrics, NetworkPerformanceMetrics)
        assert isinstance(network_state.intelligence_insights, IntelligenceInsights)


class TestAgentNetworkIntegration:
    """Test integration between Network Coordinator and Agent Registry."""
    
    @pytest.fixture
    async def integrated_system(self):
        """Create an integrated agent network system."""
        coordinator = NetworkCoordinator()
        registry = AgentRegistry()
        
        await coordinator.start()
        await registry.start()
        
        yield coordinator, registry
        
        await coordinator.stop()
        await registry.stop()
    
    @pytest.mark.asyncio
    async def test_registry_coordinator_integration(self, integrated_system):
        """Test integration between registry and coordinator."""
        coordinator, registry = integrated_system
        
        # Register agents in registry
        await registry.register_agent("agent1", "consensus", ["voting"])
        await registry.register_agent("agent2", "orchestration", ["task_distribution"])
        
        # Update coordinator's network state with registry agents
        all_agents = registry.get_all_agents()
        coordinator.network_state.active_agents.update(all_agents)
        
        # Test that coordinator can see registry agents
        assert len(coordinator.network_state.active_agents) == 2
        assert "agent1" in coordinator.network_state.active_agents
        assert "agent2" in coordinator.network_state.active_agents
        
        # Test health monitoring with registry agents
        health_report = await coordinator.monitor_network_health()
        assert health_report["agent_health"]["total_agents"] == 2
    
    @pytest.mark.asyncio
    async def test_performance_tracking_integration(self, integrated_system):
        """Test performance tracking integration."""
        coordinator, registry = integrated_system
        
        # Register agent
        await registry.register_agent("agent1", "consensus", ["voting"])
        
        # Track performance in registry
        metric = PerformanceMetric("coordination_time", 50.0, "milliseconds")
        await registry.track_agent_performance("agent1", metric)
        
        # Verify performance is tracked
        agent_info = registry.get_agent_info("agent1")
        assert len(agent_info.performance_history) == 1
        assert agent_info.performance_history[0].metric_name == "coordination_time"
    
    @pytest.mark.asyncio
    async def test_agent_discovery_for_coordination(self, integrated_system):
        """Test using agent discovery for coordination tasks."""
        coordinator, registry = integrated_system
        
        # Register agents with different capabilities
        await registry.register_agent("agent1", "consensus", ["voting", "analysis"])
        await registry.register_agent("agent2", "orchestration", ["task_distribution"])
        await registry.update_agent_status("agent1", AgentStatus.ACTIVE)
        await registry.update_agent_status("agent2", AgentStatus.ACTIVE)
        
        # Discover agents for coordination
        voting_agents = await registry.discover_agents(
            capabilities=["voting"],
            status=AgentStatus.ACTIVE
        )
        
        assert len(voting_agents) == 1
        assert voting_agents[0].agent_id == "agent1"
        
        # Test that coordinator could use this for task assignment
        task_requirements = {"capabilities": ["voting"]}
        # This would be used in actual coordination logic
        assert len(voting_agents) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])