"""
PDCA Orchestrator for Beast Mode Framework

Systematic orchestration of Plan-Do-Check-Act cycles across all Beast Mode
components with comprehensive tracking, optimization, and continuous improvement.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from ..core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator
from .pdca_core import PDCACore, PDCAPhase, PDCACycle, PDCAResult
from ..rca.rca_engine import RCAEngine
from ..diagnostics.tool_health_diagnostics import ToolHealthDiagnostics


logger = logging.getLogger(__name__)


class OrchestrationStrategy(Enum):
    """PDCA orchestration strategies"""
    SEQUENTIAL = "sequential"  # One cycle at a time
    PARALLEL = "parallel"     # Multiple cycles simultaneously
    ADAPTIVE = "adaptive"     # Dynamic based on system state
    PRIORITY_BASED = "priority_based"  # Based on impact/urgency


class CyclePriority(Enum):
    """Priority levels for PDCA cycles"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class OrchestrationContext:
    """Context for PDCA orchestration"""
    orchestration_id: str
    strategy: OrchestrationStrategy
    max_concurrent_cycles: int = 3
    priority_threshold: CyclePriority = CyclePriority.MEDIUM
    timeout_minutes: int = 30
    auto_escalation: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'orchestration_id': self.orchestration_id,
            'strategy': self.strategy.value,
            'max_concurrent_cycles': self.max_concurrent_cycles,
            'priority_threshold': self.priority_threshold.value,
            'timeout_minutes': self.timeout_minutes,
            'auto_escalation': self.auto_escalation
        }


@dataclass
class CycleExecution:
    """Tracks execution of a PDCA cycle"""
    cycle_id: str
    component_name: str
    priority: CyclePriority
    started_at: datetime
    current_phase: PDCAPhase
    progress_percentage: float = 0.0
    completed_at: Optional[datetime] = None
    result: Optional[PDCAResult] = None
    error_message: Optional[str] = None
    
    def is_complete(self) -> bool:
        return self.completed_at is not None
    
    def is_successful(self) -> bool:
        return self.is_complete() and self.result and self.result.success
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cycle_id': self.cycle_id,
            'component_name': self.component_name,
            'priority': self.priority.value,
            'started_at': self.started_at.isoformat(),
            'current_phase': self.current_phase.value,
            'progress_percentage': self.progress_percentage,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result.to_dict() if self.result else None,
            'error_message': self.error_message
        }


@dataclass
class OrchestrationMetrics:
    """Metrics for PDCA orchestration performance"""
    total_cycles_executed: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    average_cycle_duration_minutes: float = 0.0
    improvement_rate: float = 0.0
    concurrent_cycles_peak: int = 0
    
    def success_rate(self) -> float:
        if self.total_cycles_executed == 0:
            return 0.0
        return self.successful_cycles / self.total_cycles_executed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_cycles_executed': self.total_cycles_executed,
            'successful_cycles': self.successful_cycles,
            'failed_cycles': self.failed_cycles,
            'success_rate': self.success_rate(),
            'average_cycle_duration_minutes': self.average_cycle_duration_minutes,
            'improvement_rate': self.improvement_rate,
            'concurrent_cycles_peak': self.concurrent_cycles_peak
        }


class PDCAOrchestrator(ReflectiveModule):
    """
    Systematic orchestration of PDCA cycles across Beast Mode components.
    
    Features:
    - Multi-strategy orchestration (sequential, parallel, adaptive, priority-based)
    - Comprehensive cycle tracking and performance monitoring
    - Automatic escalation and error handling with RCA integration
    - Cross-component coordination and dependency management
    - Continuous improvement through systematic learning
    """
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.pdca_core = PDCACore()
        self.rca_engine = RCAEngine()
        self.health_diagnostics = ToolHealthDiagnostics()
        
        # Orchestration state
        self.active_executions: Dict[str, CycleExecution] = {}
        self.execution_history: List[CycleExecution] = []
        self.registered_components: Dict[str, ReflectiveModule] = {}
        
        # Configuration
        self.default_context = OrchestrationContext(
            orchestration_id="default",
            strategy=OrchestrationStrategy.ADAPTIVE,
            max_concurrent_cycles=3,
            priority_threshold=CyclePriority.MEDIUM
        )
        
        # Metrics
        self.metrics = OrchestrationMetrics()
        
        # Improvement tracking
        self.improvement_history: List[Dict[str, Any]] = []
        
        logger.info("PDCA Orchestrator initialized")
    
    def register_component(self, name: str, component: ReflectiveModule):
        """Register a component for PDCA orchestration"""
        self.registered_components[name] = component
        logger.info(f"Registered component for PDCA orchestration: {name}")
    
    async def orchestrate_systematic_improvement(self, 
                                               context: Optional[OrchestrationContext] = None) -> Dict[str, Any]:
        """
        Orchestrate systematic improvement across all registered components.
        
        Args:
            context: Orchestration context (uses default if None)
            
        Returns:
            Orchestration results and metrics
        """
        if context is None:
            context = self.default_context
        
        logger.info(f"Starting systematic improvement orchestration: {context.strategy.value}")
        
        try:
            # Assess component health and prioritize
            component_assessments = await self._assess_component_health()
            
            # Plan PDCA cycles based on strategy
            planned_cycles = await self._plan_pdca_cycles(component_assessments, context)
            
            # Execute cycles according to strategy
            execution_results = await self._execute_cycles(planned_cycles, context)
            
            # Analyze results and generate insights
            orchestration_insights = await self._analyze_orchestration_results(execution_results)
            
            # Update metrics
            self._update_orchestration_metrics(execution_results)
            
            return {
                'orchestration_id': context.orchestration_id,
                'strategy': context.strategy.value,
                'component_assessments': component_assessments,
                'planned_cycles': len(planned_cycles),
                'execution_results': execution_results,
                'orchestration_insights': orchestration_insights,
                'metrics': self.metrics.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            
            # Perform RCA on orchestration failure
            rca_result = await self.rca_engine.analyze_failure(
                error=str(e),
                context={'orchestration_context': context.to_dict()}
            )
            
            return {
                'orchestration_id': context.orchestration_id,
                'status': 'failed',
                'error': str(e),
                'rca_analysis': rca_result.to_dict() if rca_result else None
            }
    
    async def _assess_component_health(self) -> Dict[str, Any]:
        """Assess health of all registered components"""
        assessments = {}
        
        for name, component in self.registered_components.items():
            try:
                health_status = component.get_module_status()
                health_indicators = component.get_health_indicators()
                operational_info = component.get_operational_info()
                
                # Calculate improvement priority
                priority = self._calculate_improvement_priority(health_status, health_indicators)
                
                assessments[name] = {
                    'health_status': health_status.value,
                    'health_indicators': [hi.to_dict() for hi in health_indicators],
                    'operational_info': operational_info,
                    'improvement_priority': priority.value,
                    'needs_improvement': health_status != ModuleStatus.HEALTHY
                }
                
            except Exception as e:
                logger.error(f"Failed to assess component {name}: {e}")
                assessments[name] = {
                    'health_status': 'unknown',
                    'error': str(e),
                    'improvement_priority': CyclePriority.HIGH.value,
                    'needs_improvement': True
                }
        
        return assessments
    
    def _calculate_improvement_priority(self, status: ModuleStatus, indicators: List[HealthIndicator]) -> CyclePriority:
        """Calculate improvement priority based on health status"""
        
        if status == ModuleStatus.UNHEALTHY:
            return CyclePriority.CRITICAL
        elif status == ModuleStatus.DEGRADED:
            return CyclePriority.HIGH
        elif status == ModuleStatus.INITIALIZING:
            return CyclePriority.MEDIUM
        
        # Check indicators for issues
        degraded_indicators = [i for i in indicators if i.status == 'degraded']
        if len(degraded_indicators) > 2:
            return CyclePriority.MEDIUM
        elif len(degraded_indicators) > 0:
            return CyclePriority.LOW
        
        return CyclePriority.LOW
    
    async def _plan_pdca_cycles(self, assessments: Dict[str, Any], context: OrchestrationContext) -> List[Dict[str, Any]]:
        """Plan PDCA cycles based on component assessments"""
        
        planned_cycles = []
        
        for component_name, assessment in assessments.items():
            if assessment.get('needs_improvement', False):
                priority = CyclePriority(assessment['improvement_priority'])
                
                # Only plan cycles that meet priority threshold
                priority_values = {
                    CyclePriority.CRITICAL: 4,
                    CyclePriority.HIGH: 3,
                    CyclePriority.MEDIUM: 2,
                    CyclePriority.LOW: 1
                }
                
                if priority_values[priority] >= priority_values[context.priority_threshold]:
                    cycle_plan = {
                        'cycle_id': str(uuid.uuid4()),
                        'component_name': component_name,
                        'priority': priority,
                        'improvement_areas': self._identify_improvement_areas(assessment),
                        'estimated_duration_minutes': self._estimate_cycle_duration(priority)
                    }
                    planned_cycles.append(cycle_plan)
        
        # Sort by priority
        planned_cycles.sort(key=lambda c: priority_values[c['priority']], reverse=True)
        
        return planned_cycles
    
    def _identify_improvement_areas(self, assessment: Dict[str, Any]) -> List[str]:
        """Identify specific areas for improvement"""
        areas = []
        
        # Check health indicators
        for indicator in assessment.get('health_indicators', []):
            if indicator.get('status') == 'degraded':
                areas.append(indicator.get('name', 'unknown'))
        
        # Default improvement areas based on status
        if assessment.get('health_status') == 'unhealthy':
            areas.extend(['error_handling', 'performance_optimization', 'resource_management'])
        elif assessment.get('health_status') == 'degraded':
            areas.extend(['performance_tuning', 'monitoring_enhancement'])
        
        return areas or ['general_optimization']
    
    def _estimate_cycle_duration(self, priority: CyclePriority) -> int:
        """Estimate PDCA cycle duration based on priority"""
        duration_map = {
            CyclePriority.CRITICAL: 15,  # 15 minutes
            CyclePriority.HIGH: 20,     # 20 minutes
            CyclePriority.MEDIUM: 25,   # 25 minutes
            CyclePriority.LOW: 30       # 30 minutes
        }
        return duration_map.get(priority, 25)
    
    async def _execute_cycles(self, planned_cycles: List[Dict[str, Any]], context: OrchestrationContext) -> List[Dict[str, Any]]:
        """Execute planned PDCA cycles according to strategy"""
        
        if context.strategy == OrchestrationStrategy.SEQUENTIAL:
            return await self._execute_sequential(planned_cycles)
        elif context.strategy == OrchestrationStrategy.PARALLEL:
            return await self._execute_parallel(planned_cycles, context.max_concurrent_cycles)
        elif context.strategy == OrchestrationStrategy.ADAPTIVE:
            return await self._execute_adaptive(planned_cycles, context)
        elif context.strategy == OrchestrationStrategy.PRIORITY_BASED:
            return await self._execute_priority_based(planned_cycles, context)
        else:
            raise ValueError(f"Unknown orchestration strategy: {context.strategy}")
    
    async def _execute_sequential(self, planned_cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute cycles sequentially"""
        results = []
        
        for cycle_plan in planned_cycles:
            try:
                result = await self._execute_single_cycle(cycle_plan)
                results.append(result)
            except Exception as e:
                logger.error(f"Sequential cycle execution failed: {e}")
                results.append({
                    'cycle_id': cycle_plan['cycle_id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    async def _execute_parallel(self, planned_cycles: List[Dict[str, Any]], max_concurrent: int) -> List[Dict[str, Any]]:
        """Execute cycles in parallel with concurrency limit"""
        results = []
        
        # Execute in batches
        for i in range(0, len(planned_cycles), max_concurrent):
            batch = planned_cycles[i:i + max_concurrent]
            
            # Execute batch concurrently
            batch_tasks = [self._execute_single_cycle(cycle_plan) for cycle_plan in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        'cycle_id': batch[j]['cycle_id'],
                        'status': 'failed',
                        'error': str(result)
                    })
                else:
                    results.append(result)
        
        return results
    
    async def _execute_adaptive(self, planned_cycles: List[Dict[str, Any]], context: OrchestrationContext) -> List[Dict[str, Any]]:
        """Execute cycles adaptively based on system state"""
        
        # Start with parallel execution for high-priority cycles
        high_priority_cycles = [c for c in planned_cycles if c['priority'] in [CyclePriority.CRITICAL, CyclePriority.HIGH]]
        other_cycles = [c for c in planned_cycles if c['priority'] not in [CyclePriority.CRITICAL, CyclePriority.HIGH]]
        
        results = []
        
        # Execute high-priority cycles in parallel
        if high_priority_cycles:
            high_priority_results = await self._execute_parallel(high_priority_cycles, context.max_concurrent_cycles)
            results.extend(high_priority_results)
        
        # Execute remaining cycles sequentially to avoid resource contention
        if other_cycles:
            other_results = await self._execute_sequential(other_cycles)
            results.extend(other_results)
        
        return results
    
    async def _execute_priority_based(self, planned_cycles: List[Dict[str, Any]], context: OrchestrationContext) -> List[Dict[str, Any]]:
        """Execute cycles based on priority with dynamic scheduling"""
        
        # Group by priority
        priority_groups = {
            CyclePriority.CRITICAL: [],
            CyclePriority.HIGH: [],
            CyclePriority.MEDIUM: [],
            CyclePriority.LOW: []
        }
        
        for cycle in planned_cycles:
            priority_groups[cycle['priority']].append(cycle)
        
        results = []
        
        # Execute in priority order
        for priority in [CyclePriority.CRITICAL, CyclePriority.HIGH, CyclePriority.MEDIUM, CyclePriority.LOW]:
            if priority_groups[priority]:
                # Critical and high priority: parallel execution
                if priority in [CyclePriority.CRITICAL, CyclePriority.HIGH]:
                    priority_results = await self._execute_parallel(priority_groups[priority], context.max_concurrent_cycles)
                else:
                    # Medium and low priority: sequential execution
                    priority_results = await self._execute_sequential(priority_groups[priority])
                
                results.extend(priority_results)
        
        return results
    
    async def _execute_single_cycle(self, cycle_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single PDCA cycle"""
        
        component_name = cycle_plan['component_name']
        component = self.registered_components[component_name]
        
        # Create execution tracking
        execution = CycleExecution(
            cycle_id=cycle_plan['cycle_id'],
            component_name=component_name,
            priority=cycle_plan['priority'],
            started_at=datetime.utcnow(),
            current_phase=PDCAPhase.PLAN
        )
        
        self.active_executions[cycle_plan['cycle_id']] = execution
        
        try:
            # Execute PDCA cycle
            cycle_result = await self.pdca_core.execute_cycle(
                component=component,
                improvement_areas=cycle_plan['improvement_areas']
            )
            
            execution.result = cycle_result
            execution.completed_at = datetime.utcnow()
            execution.progress_percentage = 100.0
            
            # Move to history
            self.execution_history.append(execution)
            del self.active_executions[cycle_plan['cycle_id']]
            
            return {
                'cycle_id': cycle_plan['cycle_id'],
                'component_name': component_name,
                'status': 'completed',
                'result': cycle_result.to_dict(),
                'duration_minutes': (execution.completed_at - execution.started_at).total_seconds() / 60
            }
            
        except Exception as e:
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            # Move to history
            self.execution_history.append(execution)
            del self.active_executions[cycle_plan['cycle_id']]
            
            raise
    
    async def _analyze_orchestration_results(self, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze orchestration results and generate insights"""
        
        successful_cycles = [r for r in execution_results if r.get('status') == 'completed']
        failed_cycles = [r for r in execution_results if r.get('status') == 'failed']
        
        total_improvement = sum(
            r.get('result', {}).get('improvement_achieved', 0.0) 
            for r in successful_cycles
        )
        
        insights = {
            'total_cycles': len(execution_results),
            'successful_cycles': len(successful_cycles),
            'failed_cycles': len(failed_cycles),
            'success_rate': len(successful_cycles) / len(execution_results) if execution_results else 0.0,
            'total_improvement': total_improvement,
            'average_cycle_duration': self._calculate_average_duration(successful_cycles),
            'lessons_learned': self._extract_lessons_learned(successful_cycles),
            'failure_analysis': self._analyze_failures(failed_cycles)
        }
        
        return insights
    
    def _calculate_average_duration(self, successful_cycles: List[Dict[str, Any]]) -> float:
        """Calculate average cycle duration"""
        if not successful_cycles:
            return 0.0
        
        durations = [c.get('duration_minutes', 0.0) for c in successful_cycles]
        return sum(durations) / len(durations)
    
    def _extract_lessons_learned(self, successful_cycles: List[Dict[str, Any]]) -> List[str]:
        """Extract lessons learned from successful cycles"""
        lessons = []
        
        for cycle in successful_cycles:
            result = cycle.get('result', {})
            cycle_lessons = result.get('lessons_learned', [])
            lessons.extend(cycle_lessons)
        
        return lessons
    
    def _analyze_failures(self, failed_cycles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failed cycles for patterns"""
        if not failed_cycles:
            return {'failure_count': 0}
        
        failure_reasons = [c.get('error', 'unknown') for c in failed_cycles]
        
        return {
            'failure_count': len(failed_cycles),
            'common_failures': failure_reasons,
            'recommendations': [
                'Review component health before cycle execution',
                'Implement better error handling in PDCA cycles',
                'Add pre-cycle validation checks'
            ]
        }
    
    def _update_orchestration_metrics(self, execution_results: List[Dict[str, Any]]):
        """Update orchestration metrics"""
        successful_count = len([r for r in execution_results if r.get('status') == 'completed'])
        failed_count = len([r for r in execution_results if r.get('status') == 'failed'])
        
        self.metrics.total_cycles_executed += len(execution_results)
        self.metrics.successful_cycles += successful_count
        self.metrics.failed_cycles += failed_count
        
        # Update concurrent cycles peak
        current_concurrent = len(self.active_executions)
        if current_concurrent > self.metrics.concurrent_cycles_peak:
            self.metrics.concurrent_cycles_peak = current_concurrent
        
        # Calculate average duration
        successful_cycles = [r for r in execution_results if r.get('status') == 'completed']
        if successful_cycles:
            avg_duration = self._calculate_average_duration(successful_cycles)
            # Update running average
            total_successful = self.metrics.successful_cycles
            if total_successful > 0:
                self.metrics.average_cycle_duration_minutes = (
                    (self.metrics.average_cycle_duration_minutes * (total_successful - successful_count) + 
                     avg_duration * successful_count) / total_successful
                )
    
    # ReflectiveModule implementation
    
    def get_module_status(self) -> ModuleStatus:
        """Get current module status"""
        if len(self.registered_components) == 0:
            return ModuleStatus.INITIALIZING
        
        # Check if any cycles are failing frequently
        if self.metrics.total_cycles_executed > 0:
            success_rate = self.metrics.success_rate()
            if success_rate < 0.5:
                return ModuleStatus.UNHEALTHY
            elif success_rate < 0.8:
                return ModuleStatus.DEGRADED
        
        return ModuleStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """Check if module is healthy"""
        return self.get_module_status() in [ModuleStatus.HEALTHY, ModuleStatus.INITIALIZING]
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get health indicators"""
        indicators = []
        
        # Orchestration success rate
        if self.metrics.total_cycles_executed > 0:
            success_rate = self.metrics.success_rate()
            indicators.append(HealthIndicator(
                name="orchestration_success_rate",
                status="healthy" if success_rate > 0.8 else "degraded" if success_rate > 0.5 else "unhealthy",
                message=f"PDCA orchestration success rate: {success_rate:.1%}",
                details={'success_rate': success_rate, 'total_cycles': self.metrics.total_cycles_executed}
            ))
        
        # Active cycles
        active_count = len(self.active_executions)
        indicators.append(HealthIndicator(
            name="active_cycles",
            status="healthy" if active_count <= 5 else "degraded",
            message=f"Active PDCA cycles: {active_count}",
            details={'active_cycles': active_count, 'max_recommended': 5}
        ))
        
        # Registered components
        component_count = len(self.registered_components)
        indicators.append(HealthIndicator(
            name="registered_components",
            status="healthy" if component_count > 0 else "degraded",
            message=f"Registered components: {component_count}",
            details={'component_count': component_count}
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information"""
        return {
            'module_name': 'PDCAOrchestrator',
            'version': '1.0.0',
            'registered_components': list(self.registered_components.keys()),
            'active_executions': len(self.active_executions),
            'execution_history_size': len(self.execution_history),
            'metrics': self.metrics.to_dict(),
            'default_strategy': self.default_context.strategy.value
        }