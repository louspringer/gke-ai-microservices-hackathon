"""
Beast Mode Swarm Manager Integration

Integration layer for Multi-Instance Kiro Orchestration within the agent network.
Provides distributed swarm coordination and cross-deployment-target management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict
from enum import Enum

from ..models.data_models import (
    AgentInfo,
    AgentStatus,
    PerformanceMetric,
    SystemIntegration,
    IntegrationStatus
)
from ...core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator


class DeploymentTarget(Enum):
    """Available deployment targets for swarms."""
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    EDGE = "edge"


class SwarmStatus(Enum):
    """Status of a swarm deployment."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SCALING = "scaling"
    DEGRADED = "degraded"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class SwarmManager(ReflectiveModule):
    """
    Integration layer for Multi-Instance Kiro Orchestration.
    
    Manages distributed swarm coordination, branch management, and 
    cross-deployment-target orchestration for massive parallel development.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Swarm Manager."""
        super().__init__()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Swarm management settings
        self.max_swarm_size = self.config.get('max_swarm_size', 50)
        self.swarm_timeout_seconds = self.config.get('swarm_timeout_seconds', 300)
        self.auto_scaling_enabled = self.config.get('auto_scaling_enabled', True)
        self.branch_isolation_enabled = self.config.get('branch_isolation_enabled', True)
        
        # Multi-Instance Kiro Orchestration integration
        self.orchestration_engine = None
        
        # Integration state
        self.integration_status = IntegrationStatus.DISCONNECTED
        self.active_swarms: Dict[str, Dict[str, Any]] = {}
        self.swarm_history: List[Dict[str, Any]] = []
        
        # Deployment target management
        self.deployment_targets: Dict[DeploymentTarget, Dict[str, Any]] = {
            DeploymentTarget.LOCAL: {'available': True, 'capacity': 10},
            DeploymentTarget.CLOUD: {'available': False, 'capacity': 100},
            DeploymentTarget.HYBRID: {'available': False, 'capacity': 50},
            DeploymentTarget.EDGE: {'available': False, 'capacity': 20}
        }
        
        # Performance tracking
        self.swarm_performance_metrics: List[PerformanceMetric] = []
        self.successful_deployments = 0
        self.failed_deployments = 0
        
        self.logger.info("SwarmManager initialized")
    
    async def start(self) -> None:
        """Start the swarm manager."""
        try:
            # Initialize deployment targets
            await self._initialize_deployment_targets()
            
            # Connect to orchestration engine
            await self._connect_to_orchestration_engine()
            
            self.integration_status = IntegrationStatus.CONNECTED
            self.logger.info("SwarmManager started successfully")
        except Exception as e:
            self.integration_status = IntegrationStatus.ERROR
            self.logger.error(f"Failed to start SwarmManager: {e}")
    
    async def stop(self) -> None:
        """Stop the swarm manager."""
        # Terminate all active swarms
        for swarm_id in list(self.active_swarms.keys()):
            await self._terminate_swarm(swarm_id)
        
        self.integration_status = IntegrationStatus.DISCONNECTED
        self.logger.info("SwarmManager stopped")
    
    async def integrate_kiro_orchestration(self, orchestration_engine: Any) -> bool:
        """
        Connect with Multi-Instance Kiro Orchestration.
        
        Args:
            orchestration_engine: The orchestration engine instance to integrate with
            
        Returns:
            True if integration successful, False otherwise
        """
        try:
            self.orchestration_engine = orchestration_engine
            
            # Test the integration
            if hasattr(orchestration_engine, 'get_status'):
                status = await orchestration_engine.get_status()
                self.logger.info(f"Integrated with orchestration engine, status: {status}")
            
            self.integration_status = IntegrationStatus.CONNECTED
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to integrate orchestration engine: {e}")
            self.integration_status = IntegrationStatus.ERROR
            return False
    
    async def coordinate_distributed_swarms(
        self,
        swarm_config: Dict[str, Any],
        target_agents: List[AgentInfo],
        deployment_targets: Optional[List[DeploymentTarget]] = None
    ) -> Dict[str, Any]:
        """
        Manage swarms across deployment targets.
        
        Args:
            swarm_config: Configuration for the swarm deployment
            target_agents: Agents to include in the swarm
            deployment_targets: Preferred deployment targets
            
        Returns:
            Swarm coordination result with deployment details
        """
        swarm_id = f"swarm_{datetime.now().timestamp()}"
        start_time = datetime.now()
        
        try:
            # Validate swarm configuration
            validated_config = await self._validate_swarm_config(swarm_config)
            
            # Select optimal deployment targets
            selected_targets = await self._select_deployment_targets(
                deployment_targets, len(target_agents), validated_config
            )
            
            # Create swarm deployment plan
            deployment_plan = await self._create_swarm_deployment_plan(
                swarm_id, validated_config, target_agents, selected_targets
            )
            
            # Execute swarm deployment
            deployment_result = await self._execute_swarm_deployment(
                swarm_id, deployment_plan
            )
            
            # Monitor swarm health
            await self._start_swarm_monitoring(swarm_id)
            
            # Record performance
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._record_swarm_performance(swarm_id, execution_time, True)
            
            self.successful_deployments += 1
            
            self.logger.info(
                f"Swarm deployment completed: {swarm_id} across {len(selected_targets)} targets"
            )
            
            return {
                'success': True,
                'swarm_id': swarm_id,
                'deployment_targets': [target.value for target in selected_targets],
                'deployed_agents': len(target_agents),
                'deployment_plan': deployment_plan,
                'execution_time_seconds': execution_time
            }
            
        except Exception as e:
            self.failed_deployments += 1
            await self._record_swarm_performance(swarm_id, 0, False)
            
            self.logger.error(f"Swarm deployment failed: {swarm_id} - {e}")
            
            return {
                'success': False,
                'swarm_id': swarm_id,
                'error': str(e),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    async def handle_branch_coordination(
        self,
        branch_config: Dict[str, Any],
        participating_agents: List[AgentInfo]
    ) -> Dict[str, Any]:
        """
        Coordinate branch isolation and merging across swarms.
        
        Args:
            branch_config: Configuration for branch operations
            participating_agents: Agents participating in branch operations
            
        Returns:
            Branch coordination result
        """
        try:
            if not self.branch_isolation_enabled:
                return {
                    'success': False,
                    'error': 'Branch isolation is disabled'
                }
            
            branch_id = f"branch_{datetime.now().timestamp()}"
            
            # Create isolated branch environment
            branch_environment = await self._create_branch_environment(
                branch_id, branch_config, participating_agents
            )
            
            # Coordinate branch operations
            branch_operations = await self._coordinate_branch_operations(
                branch_id, branch_environment, participating_agents
            )
            
            # Handle branch merging if requested
            merge_result = None
            if branch_config.get('auto_merge', False):
                merge_result = await self._handle_branch_merging(
                    branch_id, branch_operations
                )
            
            self.logger.info(f"Branch coordination completed: {branch_id}")
            
            return {
                'success': True,
                'branch_id': branch_id,
                'branch_environment': branch_environment,
                'operations_result': branch_operations,
                'merge_result': merge_result
            }
            
        except Exception as e:
            self.logger.error(f"Branch coordination failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def optimize_swarm_composition(
        self,
        workload_requirements: Dict[str, Any],
        available_agents: List[AgentInfo]
    ) -> Dict[str, Any]:
        """
        Determine optimal swarm size and composition.
        
        Args:
            workload_requirements: Requirements for the workload
            available_agents: Available agents for swarm composition
            
        Returns:
            Optimal swarm composition recommendation
        """
        try:
            # Analyze workload requirements
            workload_analysis = await self._analyze_workload_requirements(
                workload_requirements
            )
            
            # Score agents for suitability
            agent_scores = await self._score_agents_for_workload(
                available_agents, workload_analysis
            )
            
            # Determine optimal swarm size
            optimal_size = await self._calculate_optimal_swarm_size(
                workload_analysis, len(available_agents)
            )
            
            # Select best agents for swarm
            selected_agents = await self._select_optimal_agents(
                agent_scores, optimal_size, available_agents
            )
            
            # Calculate expected performance
            expected_performance = await self._calculate_expected_performance(
                selected_agents, workload_analysis
            )
            
            self.logger.info(
                f"Swarm composition optimized: {len(selected_agents)} agents selected"
            )
            
            return {
                'success': True,
                'optimal_size': optimal_size,
                'selected_agents': [agent.agent_id for agent in selected_agents],
                'agent_scores': agent_scores,
                'expected_performance': expected_performance,
                'workload_analysis': workload_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Swarm composition optimization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_integration_status(self) -> SystemIntegration:
        """Get the current integration status."""
        return SystemIntegration(
            system_name="orchestration",
            integration_status=self.integration_status,
            active_agents=self._get_active_swarm_agents(),
            coordination_overhead=self._calculate_average_coordination_overhead(),
            success_rate=self._calculate_success_rate(),
            last_health_check=datetime.now(),
            error_count=self.failed_deployments
        )
    
    def get_swarm_statistics(self) -> Dict[str, Any]:
        """Get swarm operation statistics."""
        return {
            'active_swarms': len(self.active_swarms),
            'total_deployments': len(self.swarm_history),
            'successful_deployments': self.successful_deployments,
            'failed_deployments': self.failed_deployments,
            'success_rate': self._calculate_success_rate(),
            'average_swarm_size': self._calculate_average_swarm_size(),
            'deployment_targets': {
                target.value: info for target, info in self.deployment_targets.items()
            },
            'integration_status': self.integration_status.value
        }
    
    # ReflectiveModule implementation
    
    def get_module_status(self) -> ModuleStatus:
        """Get the current operational status of the swarm manager."""
        if self.integration_status == IntegrationStatus.DISCONNECTED:
            return ModuleStatus.SHUTDOWN
        elif self.integration_status == IntegrationStatus.ERROR:
            return ModuleStatus.UNHEALTHY
        elif self.integration_status == IntegrationStatus.CONNECTING:
            return ModuleStatus.INITIALIZING
        else:
            # Check performance metrics
            success_rate = self._calculate_success_rate()
            if success_rate >= 0.8:
                return ModuleStatus.HEALTHY
            elif success_rate >= 0.5:
                return ModuleStatus.DEGRADED
            else:
                return ModuleStatus.UNHEALTHY
    
    def is_healthy(self) -> bool:
        """Check if the swarm manager is currently healthy."""
        return (self.integration_status == IntegrationStatus.CONNECTED and
                self._calculate_success_rate() >= 0.5)
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get detailed health indicators for the swarm manager."""
        indicators = []
        
        # Integration status
        indicators.append(HealthIndicator(
            name="integration_status",
            status="healthy" if self.integration_status == IntegrationStatus.CONNECTED else "unhealthy",
            message=f"Orchestration engine integration: {self.integration_status.value}"
        ))
        
        # Success rate
        success_rate = self._calculate_success_rate()
        indicators.append(HealthIndicator(
            name="swarm_success_rate",
            status="healthy" if success_rate >= 0.8 else "degraded",
            message=f"Swarm deployment success rate: {success_rate:.1%}",
            details={"successful": self.successful_deployments, "failed": self.failed_deployments}
        ))
        
        # Active swarms
        active_swarms = len(self.active_swarms)
        indicators.append(HealthIndicator(
            name="active_swarms",
            status="healthy" if active_swarms <= 10 else "degraded",
            message=f"Active swarms: {active_swarms}",
            details={"active": active_swarms, "max_recommended": 10}
        ))
        
        # Deployment target availability
        available_targets = sum(1 for target_info in self.deployment_targets.values() 
                              if target_info.get('available', False))
        total_targets = len(self.deployment_targets)
        
        indicators.append(HealthIndicator(
            name="deployment_targets",
            status="healthy" if available_targets >= 1 else "unhealthy",
            message=f"Available deployment targets: {available_targets}/{total_targets}",
            details={"available": available_targets, "total": total_targets}
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information about the swarm manager."""
        return {
            "module_type": "SwarmManager",
            "integration_status": self.integration_status.value,
            "configuration": {
                "max_swarm_size": self.max_swarm_size,
                "swarm_timeout_seconds": self.swarm_timeout_seconds,
                "auto_scaling_enabled": self.auto_scaling_enabled,
                "branch_isolation_enabled": self.branch_isolation_enabled
            },
            "statistics": self.get_swarm_statistics(),
            "active_swarms": {
                swarm_id: {
                    "status": swarm.get('status', 'unknown'),
                    "agents": len(swarm.get('agents', [])),
                    "deployment_targets": swarm.get('deployment_targets', []),
                    "uptime_seconds": (datetime.now() - swarm['start_time']).total_seconds()
                }
                for swarm_id, swarm in self.active_swarms.items()
            },
            "deployment_targets": {
                target.value: {
                    "available": info.get('available', False),
                    "capacity": info.get('capacity', 0),
                    "current_load": info.get('current_load', 0)
                }
                for target, info in self.deployment_targets.items()
            },
            "recent_performance": [
                {
                    "metric_name": metric.metric_name,
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat()
                }
                for metric in self.swarm_performance_metrics[-10:]  # Last 10 metrics
            ],
            "capabilities": [
                "distributed_swarm_coordination",
                "branch_isolation_management",
                "cross_deployment_orchestration",
                "auto_scaling",
                "swarm_optimization"
            ],
            "uptime_seconds": self.get_uptime()
        }
    
    # Private methods for internal swarm operations
    
    async def _initialize_deployment_targets(self) -> None:
        """Initialize available deployment targets."""
        # Check local deployment availability
        self.deployment_targets[DeploymentTarget.LOCAL]['available'] = True
        
        # Check cloud deployment availability (placeholder)
        # In real implementation, this would check cloud credentials and connectivity
        
        self.logger.info("Deployment targets initialized")
    
    async def _connect_to_orchestration_engine(self) -> None:
        """Attempt to connect to the orchestration engine."""
        # Placeholder - will be implemented when orchestration engine is available
        self.logger.info("Orchestration engine connection placeholder")
    
    async def _validate_swarm_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize swarm configuration."""
        validated_config = config.copy()
        
        # Set defaults
        validated_config.setdefault('max_agents', self.max_swarm_size)
        validated_config.setdefault('timeout_seconds', self.swarm_timeout_seconds)
        validated_config.setdefault('auto_scaling', self.auto_scaling_enabled)
        
        # Validate limits
        if validated_config['max_agents'] > self.max_swarm_size:
            validated_config['max_agents'] = self.max_swarm_size
            self.logger.warning(f"Swarm size limited to {self.max_swarm_size}")
        
        return validated_config
    
    async def _select_deployment_targets(
        self,
        preferred_targets: Optional[List[DeploymentTarget]],
        agent_count: int,
        config: Dict[str, Any]
    ) -> List[DeploymentTarget]:
        """Select optimal deployment targets for the swarm."""
        available_targets = [
            target for target, info in self.deployment_targets.items()
            if info.get('available', False)
        ]
        
        if not available_targets:
            raise ValueError("No deployment targets available")
        
        # If preferred targets specified, filter to available ones
        if preferred_targets:
            selected_targets = [
                target for target in preferred_targets
                if target in available_targets
            ]
            if selected_targets:
                return selected_targets
        
        # Select based on capacity and agent count
        suitable_targets = [
            target for target in available_targets
            if self.deployment_targets[target]['capacity'] >= agent_count
        ]
        
        if suitable_targets:
            return [suitable_targets[0]]  # Select first suitable target
        else:
            return [available_targets[0]]  # Fallback to first available
    
    async def _create_swarm_deployment_plan(
        self,
        swarm_id: str,
        config: Dict[str, Any],
        agents: List[AgentInfo],
        targets: List[DeploymentTarget]
    ) -> Dict[str, Any]:
        """Create a deployment plan for the swarm."""
        # Distribute agents across targets
        agents_per_target = len(agents) // len(targets)
        remainder = len(agents) % len(targets)
        
        deployment_plan = {
            'swarm_id': swarm_id,
            'total_agents': len(agents),
            'deployment_targets': len(targets),
            'target_distribution': {}
        }
        
        agent_index = 0
        for i, target in enumerate(targets):
            target_agent_count = agents_per_target + (1 if i < remainder else 0)
            target_agents = agents[agent_index:agent_index + target_agent_count]
            
            deployment_plan['target_distribution'][target.value] = {
                'agents': [agent.agent_id for agent in target_agents],
                'agent_count': len(target_agents)
            }
            
            agent_index += target_agent_count
        
        return deployment_plan
    
    async def _execute_swarm_deployment(
        self,
        swarm_id: str,
        deployment_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the swarm deployment plan."""
        # Create swarm record
        swarm_record = {
            'swarm_id': swarm_id,
            'status': SwarmStatus.INITIALIZING,
            'deployment_plan': deployment_plan,
            'start_time': datetime.now(),
            'agents': [],
            'deployment_targets': list(deployment_plan['target_distribution'].keys())
        }
        
        self.active_swarms[swarm_id] = swarm_record
        
        try:
            # Deploy to each target
            deployment_results = {}
            
            for target_name, target_config in deployment_plan['target_distribution'].items():
                target_result = await self._deploy_to_target(
                    swarm_id, target_name, target_config
                )
                deployment_results[target_name] = target_result
            
            # Update swarm status
            swarm_record['status'] = SwarmStatus.ACTIVE
            swarm_record['deployment_results'] = deployment_results
            
            return {
                'deployment_status': 'success',
                'deployed_targets': len(deployment_results),
                'deployment_results': deployment_results
            }
            
        except Exception as e:
            swarm_record['status'] = SwarmStatus.DEGRADED
            swarm_record['error'] = str(e)
            raise
    
    async def _deploy_to_target(
        self,
        swarm_id: str,
        target_name: str,
        target_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy agents to a specific target."""
        # Placeholder implementation
        await asyncio.sleep(0.1)  # Simulate deployment time
        
        return {
            'target': target_name,
            'deployed_agents': target_config['agent_count'],
            'deployment_time': datetime.now().isoformat(),
            'status': 'success'
        }
    
    async def _start_swarm_monitoring(self, swarm_id: str) -> None:
        """Start monitoring for a deployed swarm."""
        # Placeholder for swarm monitoring
        self.logger.debug(f"Started monitoring for swarm {swarm_id}")
    
    async def _terminate_swarm(self, swarm_id: str) -> None:
        """Terminate an active swarm."""
        if swarm_id in self.active_swarms:
            swarm = self.active_swarms[swarm_id]
            swarm['status'] = SwarmStatus.TERMINATING
            
            # Simulate termination process
            await asyncio.sleep(0.1)
            
            swarm['status'] = SwarmStatus.TERMINATED
            swarm['end_time'] = datetime.now()
            
            # Move to history
            self.swarm_history.append(swarm)
            del self.active_swarms[swarm_id]
            
            self.logger.info(f"Terminated swarm: {swarm_id}")
    
    async def _record_swarm_performance(
        self,
        swarm_id: str,
        execution_time: float,
        success: bool
    ) -> None:
        """Record performance metrics for swarm operations."""
        metric = PerformanceMetric(
            metric_name="swarm_deployment_time",
            value=execution_time,
            unit="seconds",
            metadata={
                'swarm_id': swarm_id,
                'success': success
            }
        )
        
        self.swarm_performance_metrics.append(metric)
        
        # Limit history size
        if len(self.swarm_performance_metrics) > 1000:
            self.swarm_performance_metrics = self.swarm_performance_metrics[-1000:]
    
    async def _create_branch_environment(
        self,
        branch_id: str,
        config: Dict[str, Any],
        agents: List[AgentInfo]
    ) -> Dict[str, Any]:
        """Create an isolated branch environment."""
        return {
            'branch_id': branch_id,
            'isolation_level': config.get('isolation_level', 'workspace'),
            'participating_agents': [agent.agent_id for agent in agents],
            'created_at': datetime.now().isoformat()
        }
    
    async def _coordinate_branch_operations(
        self,
        branch_id: str,
        environment: Dict[str, Any],
        agents: List[AgentInfo]
    ) -> Dict[str, Any]:
        """Coordinate operations within a branch environment."""
        return {
            'operations_completed': True,
            'participating_agents': len(agents),
            'operation_time': datetime.now().isoformat()
        }
    
    async def _handle_branch_merging(
        self,
        branch_id: str,
        operations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle merging of branch operations."""
        return {
            'merge_status': 'success',
            'merge_time': datetime.now().isoformat(),
            'conflicts_resolved': 0
        }
    
    async def _analyze_workload_requirements(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze workload requirements for swarm optimization."""
        return {
            'complexity': requirements.get('complexity', 'medium'),
            'parallelization_potential': requirements.get('parallelization', 0.8),
            'resource_intensity': requirements.get('resource_intensity', 'medium'),
            'estimated_duration': requirements.get('duration_hours', 1.0)
        }
    
    async def _score_agents_for_workload(
        self,
        agents: List[AgentInfo],
        workload_analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """Score agents for their suitability for the workload."""
        scores = {}
        
        for agent in agents:
            base_score = 0.5
            
            # Factor in agent status
            if agent.current_status == AgentStatus.ACTIVE:
                base_score += 0.3
            elif agent.current_status == AgentStatus.IDLE:
                base_score += 0.2
            
            # Factor in performance history
            if agent.performance_history:
                recent_performance = agent.performance_history[-5:]
                avg_performance = sum(metric.value for metric in recent_performance) / len(recent_performance)
                base_score = (base_score + avg_performance) / 2
            
            scores[agent.agent_id] = min(1.0, max(0.0, base_score))
        
        return scores
    
    async def _calculate_optimal_swarm_size(
        self,
        workload_analysis: Dict[str, Any],
        available_agents: int
    ) -> int:
        """Calculate the optimal swarm size for the workload."""
        parallelization = workload_analysis.get('parallelization_potential', 0.5)
        complexity = workload_analysis.get('complexity', 'medium')
        
        # Base size calculation
        if complexity == 'low':
            base_size = 2
        elif complexity == 'medium':
            base_size = 5
        else:  # high
            base_size = 10
        
        # Adjust for parallelization potential
        optimal_size = int(base_size * (1 + parallelization))
        
        # Limit to available agents and max swarm size
        return min(optimal_size, available_agents, self.max_swarm_size)
    
    async def _select_optimal_agents(
        self,
        agent_scores: Dict[str, float],
        target_size: int,
        available_agents: List[AgentInfo]
    ) -> List[AgentInfo]:
        """Select the best agents for the swarm."""
        # Create agent lookup
        agent_lookup = {agent.agent_id: agent for agent in available_agents}
        
        # Sort agents by score (highest first)
        sorted_agent_ids = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top agents up to target size
        selected_agents = []
        for agent_id, score in sorted_agent_ids[:target_size]:
            if agent_id in agent_lookup:
                selected_agents.append(agent_lookup[agent_id])
        
        return selected_agents
    
    async def _calculate_expected_performance(
        self,
        selected_agents: List[AgentInfo],
        workload_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate expected performance for the selected swarm."""
        if not selected_agents:
            return {'efficiency': 0.0, 'completion_time_hours': float('inf')}
        
        # Calculate average agent performance
        total_performance = 0.0
        for agent in selected_agents:
            if agent.performance_history:
                recent_performance = agent.performance_history[-5:]
                avg_performance = sum(metric.value for metric in recent_performance) / len(recent_performance)
                total_performance += avg_performance
            else:
                total_performance += 0.5  # Default performance
        
        average_performance = total_performance / len(selected_agents)
        
        # Factor in parallelization
        parallelization = workload_analysis.get('parallelization_potential', 0.5)
        swarm_efficiency = average_performance * (1 + parallelization * (len(selected_agents) - 1) / len(selected_agents))
        
        # Estimate completion time
        base_duration = workload_analysis.get('estimated_duration', 1.0)
        estimated_completion_time = base_duration / max(swarm_efficiency, 0.1)
        
        return {
            'efficiency': min(1.0, swarm_efficiency),
            'completion_time_hours': estimated_completion_time,
            'average_agent_performance': average_performance,
            'parallelization_benefit': parallelization
        }
    
    def _get_active_swarm_agents(self) -> List[str]:
        """Get list of agents in active swarms."""
        agents = []
        for swarm in self.active_swarms.values():
            agents.extend(swarm.get('agents', []))
        return agents
    
    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of swarm deployments."""
        total_deployments = self.successful_deployments + self.failed_deployments
        if total_deployments == 0:
            return 1.0  # No deployments yet, assume healthy
        return self.successful_deployments / total_deployments
    
    def _calculate_average_swarm_size(self) -> float:
        """Calculate average swarm size."""
        if not self.swarm_history and not self.active_swarms:
            return 0.0
        
        all_swarms = list(self.swarm_history) + list(self.active_swarms.values())
        total_agents = sum(len(swarm.get('agents', [])) for swarm in all_swarms)
        
        return total_agents / len(all_swarms) if all_swarms else 0.0
    
    def _calculate_average_coordination_overhead(self) -> float:
        """Calculate average coordination overhead."""
        if not self.swarm_performance_metrics:
            return 0.0
        
        deployment_times = [
            metric.value for metric in self.swarm_performance_metrics
            if metric.metric_name == "swarm_deployment_time"
        ]
        
        if not deployment_times:
            return 0.0
        
        avg_time = sum(deployment_times) / len(deployment_times)
        return avg_time * 1000  # Convert to milliseconds