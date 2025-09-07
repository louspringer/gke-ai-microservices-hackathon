"""
Tests for Beast Mode Agent Network Integration Layers

Comprehensive test suite for the system integration components.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.beast_mode.agent_network.integrations.consensus_orchestrator import ConsensusOrchestrator
from src.beast_mode.agent_network.integrations.swarm_manager import SwarmManager, DeploymentTarget
from src.beast_mode.agent_network.integrations.dag_agent_coordinator import DAGAgentCoordinator
from src.beast_mode.agent_network.models.data_models import (
    AgentInfo,
    AgentStatus,
    PerformanceMetric,
    IntegrationStatus
)


class TestConsensusOrchestrator:
    """Test the Consensus Orchestrator integration."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create a test consensus orchestrator."""
        orchestrator = ConsensusOrchestrator(config={
            'consensus_timeout_seconds': 10,
            'confidence_threshold': 0.6,
            'max_consensus_participants': 5
        })
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test consensus orchestrator initialization."""
        assert orchestrator.integration_status == IntegrationStatus.CONNECTED
        assert orchestrator.consensus_timeout_seconds == 10
        assert orchestrator.confidence_threshold == 0.6
        assert orchestrator.max_consensus_participants == 5
    
    @pytest.mark.asyncio
    async def test_consensus_engine_integration(self, orchestrator):
        """Test consensus engine integration."""
        # Create mock consensus engine
        mock_engine = Mock()
        mock_engine.get_status = AsyncMock(return_value="healthy")
        
        # Test integration
        success = await orchestrator.integrate_consensus_engine(mock_engine)
        
        assert success is True
        assert orchestrator.consensus_engine == mock_engine
        assert orchestrator.integration_status == IntegrationStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_coordinate_consensus_decisions(self, orchestrator):
        """Test consensus decision coordination."""
        # Create test agents
        agents = [
            AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE),
            AgentInfo("agent2", "consensus", ["analysis"], AgentStatus.ACTIVE),
            AgentInfo("agent3", "orchestration", ["coordination"], AgentStatus.ACTIVE)
        ]
        
        # Create decision context
        decision_context = {
            "type": "resource_allocation",
            "urgency": "medium",
            "scope": "network_wide"
        }
        
        decision_options = [
            {"option_id": "option1", "description": "Allocate to consensus agents"},
            {"option_id": "option2", "description": "Allocate to orchestration agents"}
        ]
        
        # Test consensus coordination
        result = await orchestrator.coordinate_consensus_decisions(
            decision_context, agents, decision_options
        )
        
        assert result["success"] is True
        assert "session_id" in result
        assert "decision" in result
        assert "confidence_scores" in result
        assert "execution_time_seconds" in result
        assert result["participants"] == len(agents)
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, orchestrator):
        """Test confidence scoring functionality."""
        # Create test agents with performance history
        agent1 = AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE)
        agent1.performance_history = [
            PerformanceMetric("task_success", 0.9, "ratio"),
            PerformanceMetric("response_time", 1.2, "seconds")
        ]
        
        agent2 = AgentInfo("agent2", "consensus", ["analysis"], AgentStatus.IDLE)
        agent2.performance_history = [
            PerformanceMetric("task_success", 0.7, "ratio")
        ]
        
        agents = [agent1, agent2]
        analysis_results = {"quality_score": 0.8}
        
        # Test confidence scoring
        confidence_scores = await orchestrator.apply_confidence_scoring(
            agents, analysis_results
        )
        
        assert len(confidence_scores) == 2
        assert "agent1" in confidence_scores
        assert "agent2" in confidence_scores
        assert 0.0 <= confidence_scores["agent1"] <= 1.0
        assert 0.0 <= confidence_scores["agent2"] <= 1.0
        # Active agent should have higher confidence than idle agent
        assert confidence_scores["agent1"] > confidence_scores["agent2"]
    
    @pytest.mark.asyncio
    async def test_complex_conflict_escalation(self, orchestrator):
        """Test complex conflict escalation."""
        # Create conflict scenario
        conflict_data = {
            "type": "resource_contention",
            "severity": "high",
            "systems": ["consensus", "orchestration"],
            "agents": ["agent1", "agent2", "agent3"]
        }
        
        involved_agents = [
            AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE),
            AgentInfo("agent2", "orchestration", ["coordination"], AgentStatus.ACTIVE),
            AgentInfo("agent3", "dag", ["execution"], AgentStatus.ACTIVE)
        ]
        
        # Test conflict escalation
        result = await orchestrator.escalate_complex_conflicts(
            conflict_data, involved_agents
        )
        
        assert result["success"] is True
        assert "resolution_method" in result
        assert "resolution" in result
    
    @pytest.mark.asyncio
    async def test_consensus_statistics(self, orchestrator):
        """Test consensus statistics tracking."""
        # Perform some consensus operations to generate statistics
        agents = [AgentInfo("agent1", "consensus", ["voting"], AgentStatus.ACTIVE)]
        decision_context = {"type": "test"}
        decision_options = [{"option_id": "test_option"}]
        
        await orchestrator.coordinate_consensus_decisions(
            decision_context, agents, decision_options
        )
        
        # Get statistics
        stats = orchestrator.get_consensus_statistics()
        
        assert "total_sessions" in stats
        assert "success_count" in stats
        assert "failure_count" in stats
        assert "success_rate" in stats
        assert "integration_status" in stats
        assert stats["success_count"] >= 1
    
    def test_health_indicators(self, orchestrator):
        """Test health indicators."""
        indicators = orchestrator.get_health_indicators()
        
        assert len(indicators) >= 3
        indicator_names = [ind.name for ind in indicators]
        assert "integration_status" in indicator_names
        assert "consensus_success_rate" in indicator_names
        assert "active_consensus_sessions" in indicator_names


class TestSwarmManager:
    """Test the Swarm Manager integration."""
    
    @pytest.fixture
    async def swarm_manager(self):
        """Create a test swarm manager."""
        manager = SwarmManager(config={
            'max_swarm_size': 20,
            'swarm_timeout_seconds': 60,
            'auto_scaling_enabled': True,
            'branch_isolation_enabled': True
        })
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_swarm_manager_initialization(self, swarm_manager):
        """Test swarm manager initialization."""
        assert swarm_manager.integration_status == IntegrationStatus.CONNECTED
        assert swarm_manager.max_swarm_size == 20
        assert swarm_manager.auto_scaling_enabled is True
        assert swarm_manager.branch_isolation_enabled is True
    
    @pytest.mark.asyncio
    async def test_orchestration_engine_integration(self, swarm_manager):
        """Test orchestration engine integration."""
        # Create mock orchestration engine
        mock_engine = Mock()
        mock_engine.get_status = AsyncMock(return_value="operational")
        
        # Test integration
        success = await swarm_manager.integrate_kiro_orchestration(mock_engine)
        
        assert success is True
        assert swarm_manager.orchestration_engine == mock_engine
        assert swarm_manager.integration_status == IntegrationStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_distributed_swarm_coordination(self, swarm_manager):
        """Test distributed swarm coordination."""
        # Create test agents
        agents = [
            AgentInfo(f"agent{i}", "orchestration", ["task_distribution"], AgentStatus.ACTIVE)
            for i in range(5)
        ]
        
        # Create swarm configuration
        swarm_config = {
            "max_agents": 5,
            "timeout_seconds": 30,
            "auto_scaling": True
        }
        
        deployment_targets = [DeploymentTarget.LOCAL]
        
        # Test swarm coordination
        result = await swarm_manager.coordinate_distributed_swarms(
            swarm_config, agents, deployment_targets
        )
        
        assert result["success"] is True
        assert "swarm_id" in result
        assert "deployment_targets" in result
        assert "deployed_agents" in result
        assert result["deployed_agents"] == len(agents)
        assert DeploymentTarget.LOCAL.value in result["deployment_targets"]
    
    @pytest.mark.asyncio
    async def test_branch_coordination(self, swarm_manager):
        """Test branch coordination functionality."""
        # Create test agents
        agents = [
            AgentInfo("agent1", "orchestration", ["branch_management"], AgentStatus.ACTIVE),
            AgentInfo("agent2", "orchestration", ["task_distribution"], AgentStatus.ACTIVE)
        ]
        
        # Create branch configuration
        branch_config = {
            "isolation_level": "workspace",
            "auto_merge": True,
            "branch_name": "feature/test-branch"
        }
        
        # Test branch coordination
        result = await swarm_manager.handle_branch_coordination(
            branch_config, agents
        )
        
        assert result["success"] is True
        assert "branch_id" in result
        assert "branch_environment" in result
        assert "operations_result" in result
        assert "merge_result" in result  # Should be present due to auto_merge=True
    
    @pytest.mark.asyncio
    async def test_swarm_composition_optimization(self, swarm_manager):
        """Test swarm composition optimization."""
        # Create test agents with different performance characteristics
        agents = [
            AgentInfo("high_perf_agent", "orchestration", ["optimization"], AgentStatus.ACTIVE),
            AgentInfo("medium_perf_agent", "orchestration", ["coordination"], AgentStatus.IDLE),
            AgentInfo("low_perf_agent", "orchestration", ["basic_tasks"], AgentStatus.ACTIVE)
        ]
        
        # Add performance history
        agents[0].performance_history = [PerformanceMetric("efficiency", 0.9, "ratio")]
        agents[1].performance_history = [PerformanceMetric("efficiency", 0.6, "ratio")]
        agents[2].performance_history = [PerformanceMetric("efficiency", 0.4, "ratio")]
        
        # Create workload requirements
        workload_requirements = {
            "complexity": "high",
            "parallelization": 0.8,
            "resource_intensity": "medium",
            "duration_hours": 2.0
        }
        
        # Test optimization
        result = await swarm_manager.optimize_swarm_composition(
            workload_requirements, agents
        )
        
        assert result["success"] is True
        assert "optimal_size" in result
        assert "selected_agents" in result
        assert "agent_scores" in result
        assert "expected_performance" in result
        
        # High performance agent should be selected
        assert "high_perf_agent" in result["selected_agents"]
    
    @pytest.mark.asyncio
    async def test_deployment_target_management(self, swarm_manager):
        """Test deployment target management."""
        # Check initial deployment targets
        stats = swarm_manager.get_swarm_statistics()
        deployment_targets = stats["deployment_targets"]
        
        assert DeploymentTarget.LOCAL.value in deployment_targets
        assert deployment_targets[DeploymentTarget.LOCAL.value]["available"] is True
        
        # Local should be available by default
        assert deployment_targets[DeploymentTarget.LOCAL.value]["capacity"] > 0
    
    def test_swarm_statistics(self, swarm_manager):
        """Test swarm statistics tracking."""
        stats = swarm_manager.get_swarm_statistics()
        
        assert "active_swarms" in stats
        assert "total_deployments" in stats
        assert "successful_deployments" in stats
        assert "failed_deployments" in stats
        assert "success_rate" in stats
        assert "deployment_targets" in stats
        assert "integration_status" in stats


class TestDAGAgentCoordinator:
    """Test the DAG Agent Coordinator integration."""
    
    @pytest.fixture
    async def dag_coordinator(self):
        """Create a test DAG agent coordinator."""
        coordinator = DAGAgentCoordinator(config={
            'max_parallel_tasks': 10,
            'task_timeout_seconds': 30,
            'dependency_check_interval': 0.5,
            'enable_dag_optimization': True
        })
        await coordinator.start()
        yield coordinator
        await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_dag_coordinator_initialization(self, dag_coordinator):
        """Test DAG coordinator initialization."""
        assert dag_coordinator.integration_status == IntegrationStatus.CONNECTED
        assert dag_coordinator.max_parallel_tasks == 10
        assert dag_coordinator.task_timeout_seconds == 30
        assert dag_coordinator.enable_dag_optimization is True
    
    @pytest.mark.asyncio
    async def test_framework_engine_integration(self, dag_coordinator):
        """Test framework engine integration."""
        # Create mock framework engine
        mock_engine = Mock()
        mock_engine.get_status = AsyncMock(return_value="running")
        
        # Test integration
        success = await dag_coordinator.integrate_dag_agents(mock_engine)
        
        assert success is True
        assert dag_coordinator.framework_engine == mock_engine
        assert dag_coordinator.integration_status == IntegrationStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_parallel_dag_execution(self, dag_coordinator):
        """Test parallel DAG execution coordination."""
        # Create test agents
        agents = [
            AgentInfo(f"dag_agent{i}", "dag", ["task_execution"], AgentStatus.ACTIVE)
            for i in range(3)
        ]
        
        # Create DAG definition
        dag_definition = {
            "tasks": [
                {"id": "task1", "action": "process_data"},
                {"id": "task2", "action": "analyze_results"},
                {"id": "task3", "action": "generate_report"}
            ],
            "dependencies": {
                "task2": ["task1"],
                "task3": ["task2"]
            },
            "metadata": {"name": "test_dag"}
        }
        
        execution_config = {"timeout": 60, "retry_count": 2}
        
        # Test DAG execution
        result = await dag_coordinator.coordinate_parallel_execution(
            dag_definition, agents, execution_config
        )
        
        assert result["success"] is True
        assert "dag_id" in result
        assert "execution_result" in result
        assert "execution_time_seconds" in result
        assert result["tasks_executed"] == 3
        assert result["agents_used"] == len(agents)
    
    @pytest.mark.asyncio
    async def test_dependency_management(self, dag_coordinator):
        """Test DAG dependency management."""
        # Create task dependencies
        task_dependencies = {
            "task1": [],  # No dependencies
            "task2": ["task1"],
            "task3": ["task1"],
            "task4": ["task2", "task3"]
        }
        
        execution_context = {"timeout": 30}
        
        # Test dependency management
        result = await dag_coordinator.handle_dag_dependencies(
            task_dependencies, execution_context
        )
        
        assert result["success"] is True
        assert "dependency_graph" in result
        assert "execution_order" in result
        assert "resolution_plan" in result
        assert "cycle_check" in result
        assert result["cycle_check"]["has_cycles"] is False
        
        # Check execution order makes sense
        execution_order = result["execution_order"]
        assert len(execution_order) >= 3  # Should have at least 3 levels
        assert "task1" in execution_order[0]  # task1 should be first (no deps)
        assert "task4" in execution_order[-1]  # task4 should be last (depends on others)
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, dag_coordinator):
        """Test circular dependency detection."""
        # Create circular dependencies
        task_dependencies = {
            "task1": ["task3"],
            "task2": ["task1"],
            "task3": ["task2"]
        }
        
        execution_context = {}
        
        # Test dependency management with cycles
        result = await dag_coordinator.handle_dag_dependencies(
            task_dependencies, execution_context
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Circular dependencies" in result["error"]
    
    @pytest.mark.asyncio
    async def test_dag_performance_optimization(self, dag_coordinator):
        """Test DAG performance optimization."""
        # Create DAG definition
        dag_definition = {
            "tasks": [
                {"id": "task1", "action": "load_data"},
                {"id": "task2", "action": "process_data"},
                {"id": "task3", "action": "save_results"}
            ],
            "dependencies": {
                "task2": ["task1"],
                "task3": ["task2"]
            }
        }
        
        # Create historical performance data
        historical_performance = [
            {"execution_time": 10.5, "success": True},
            {"execution_time": 12.3, "success": True},
            {"execution_time": 9.8, "success": False}
        ]
        
        # Create test agents
        agents = [
            AgentInfo("fast_agent", "dag", ["optimization"], AgentStatus.ACTIVE),
            AgentInfo("slow_agent", "dag", ["basic_execution"], AgentStatus.IDLE)
        ]
        
        # Add performance history
        agents[0].performance_history = [PerformanceMetric("speed", 0.9, "ratio")]
        agents[1].performance_history = [PerformanceMetric("speed", 0.5, "ratio")]
        
        # Test optimization
        result = await dag_coordinator.optimize_dag_performance(
            dag_definition, historical_performance, agents
        )
        
        assert result["success"] is True
        assert "dag_analysis" in result
        assert "performance_analysis" in result
        assert "agent_analysis" in result
        assert "optimizations" in result
        assert "optimized_dag" in result
    
    @pytest.mark.asyncio
    async def test_dag_execution_with_failures(self, dag_coordinator):
        """Test DAG execution handling task failures."""
        # Create agents that might fail
        agents = [
            AgentInfo("unreliable_agent", "dag", ["task_execution"], AgentStatus.ERROR)
        ]
        
        # Create simple DAG
        dag_definition = {
            "tasks": [
                {"id": "task1", "action": "might_fail"}
            ],
            "dependencies": {},
            "metadata": {"name": "failure_test_dag"}
        }
        
        # Test DAG execution (should handle gracefully)
        result = await dag_coordinator.coordinate_parallel_execution(
            dag_definition, agents, {}
        )
        
        # Should still return a result, even if execution fails
        assert "success" in result
        assert "dag_id" in result
        assert "execution_time_seconds" in result
    
    def test_dag_statistics(self, dag_coordinator):
        """Test DAG statistics tracking."""
        stats = dag_coordinator.get_dag_statistics()
        
        assert "active_dag_executions" in stats
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "success_rate" in stats
        assert "registered_tasks" in stats
        assert "dependency_relationships" in stats
        assert "integration_status" in stats
    
    def test_health_indicators(self, dag_coordinator):
        """Test health indicators."""
        indicators = dag_coordinator.get_health_indicators()
        
        assert len(indicators) >= 4
        indicator_names = [ind.name for ind in indicators]
        assert "integration_status" in indicator_names
        assert "dag_success_rate" in indicator_names
        assert "active_dag_executions" in indicator_names
        assert "task_registry" in indicator_names


class TestIntegrationLayerInteroperability:
    """Test interoperability between integration layers."""
    
    @pytest.fixture
    async def all_integrations(self):
        """Create all integration components."""
        consensus = ConsensusOrchestrator()
        swarm = SwarmManager()
        dag = DAGAgentCoordinator()
        
        await consensus.start()
        await swarm.start()
        await dag.start()
        
        yield consensus, swarm, dag
        
        await consensus.stop()
        await swarm.stop()
        await dag.stop()
    
    @pytest.mark.asyncio
    async def test_integration_status_consistency(self, all_integrations):
        """Test that all integrations report consistent status."""
        consensus, swarm, dag = all_integrations
        
        # All should be connected after start
        assert consensus.integration_status == IntegrationStatus.CONNECTED
        assert swarm.integration_status == IntegrationStatus.CONNECTED
        assert dag.integration_status == IntegrationStatus.CONNECTED
        
        # All should be healthy
        assert consensus.is_healthy() is True
        assert swarm.is_healthy() is True
        assert dag.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_cross_integration_agent_sharing(self, all_integrations):
        """Test that agents can be shared across integrations."""
        consensus, swarm, dag = all_integrations
        
        # Create agents that could work with multiple systems
        multi_system_agents = [
            AgentInfo("versatile_agent1", "consensus", ["voting", "coordination"], AgentStatus.ACTIVE),
            AgentInfo("versatile_agent2", "orchestration", ["task_distribution", "analysis"], AgentStatus.ACTIVE),
            AgentInfo("versatile_agent3", "dag", ["execution", "optimization"], AgentStatus.ACTIVE)
        ]
        
        # Test that each integration can work with these agents
        # (This is more of a conceptual test since the integrations don't directly share agents)
        
        # Consensus should be able to use agents for decisions
        decision_result = await consensus.coordinate_consensus_decisions(
            {"type": "test"}, multi_system_agents, [{"option_id": "test"}]
        )
        assert decision_result["success"] is True
        
        # Swarm should be able to coordinate these agents
        swarm_result = await swarm.coordinate_distributed_swarms(
            {"max_agents": 3}, multi_system_agents, [DeploymentTarget.LOCAL]
        )
        assert swarm_result["success"] is True
        
        # DAG should be able to execute with these agents
        dag_result = await dag.coordinate_parallel_execution(
            {"tasks": [{"id": "test_task", "action": "test"}], "dependencies": {}},
            multi_system_agents
        )
        assert dag_result["success"] is True
    
    def test_integration_health_reporting(self, all_integrations):
        """Test health reporting across all integrations."""
        consensus, swarm, dag = all_integrations
        
        # Get integration status from each
        consensus_status = consensus.get_integration_status()
        swarm_status = swarm.get_integration_status()
        dag_status = dag.get_integration_status()
        
        # All should report connected status
        assert consensus_status.integration_status == IntegrationStatus.CONNECTED
        assert swarm_status.integration_status == IntegrationStatus.CONNECTED
        assert dag_status.integration_status == IntegrationStatus.CONNECTED
        
        # All should have reasonable success rates
        assert consensus_status.success_rate >= 0.0
        assert swarm_status.success_rate >= 0.0
        assert dag_status.success_rate >= 0.0
    
    def test_operational_info_completeness(self, all_integrations):
        """Test that operational info is complete for all integrations."""
        consensus, swarm, dag = all_integrations
        
        # Get operational info from each
        consensus_info = consensus.get_operational_info()
        swarm_info = swarm.get_operational_info()
        dag_info = dag.get_operational_info()
        
        # Check required fields are present
        required_fields = ["module_type", "integration_status", "configuration", "capabilities", "uptime_seconds"]
        
        for field in required_fields:
            assert field in consensus_info
            assert field in swarm_info
            assert field in dag_info
        
        # Check module types are correct
        assert consensus_info["module_type"] == "ConsensusOrchestrator"
        assert swarm_info["module_type"] == "SwarmManager"
        assert dag_info["module_type"] == "DAGAgentCoordinator"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])