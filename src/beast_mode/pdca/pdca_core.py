"""
PDCA Core Interface for Beast Mode Framework.

This module provides systematic Plan-Do-Check-Act cycle management,
implementing the Beast Mode principle of continuous improvement through
structured methodology rather than ad-hoc approaches.
"""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import uuid

from ..core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator


class PDCAPhase(Enum):
    """Phases of the PDCA cycle."""
    PLAN = "plan"
    DO = "do" 
    CHECK = "check"
    ACT = "act"
    COMPLETE = "complete"


class CycleStatus(Enum):
    """Status of a PDCA cycle."""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PDCAPhaseResult:
    """Result of a PDCA phase execution."""
    phase: PDCAPhase
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    lessons_learned: List[str] = field(default_factory=list)
    
    def add_lesson(self, lesson: str) -> None:
        """Add a lesson learned during this phase."""
        if lesson and lesson not in self.lessons_learned:
            self.lessons_learned.append(lesson)


@dataclass
class PDCACycle:
    """
    Represents a complete PDCA cycle with systematic tracking.
    
    This class encapsulates a full Plan-Do-Check-Act cycle, providing
    systematic tracking of each phase, results, and continuous improvement
    opportunities.
    """
    
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    
    # Cycle metadata
    status: CycleStatus = CycleStatus.INITIALIZED
    current_phase: PDCAPhase = PDCAPhase.PLAN
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Phase results
    phase_results: Dict[PDCAPhase, PDCAPhaseResult] = field(default_factory=dict)
    
    # Cycle objectives and outcomes
    objectives: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    actual_outcomes: List[str] = field(default_factory=list)
    
    # Continuous improvement
    improvements_identified: List[str] = field(default_factory=list)
    next_cycle_recommendations: List[str] = field(default_factory=list)
    
    # Context and metadata
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def start_cycle(self) -> None:
        """Start the PDCA cycle."""
        if self.status == CycleStatus.INITIALIZED:
            self.status = CycleStatus.IN_PROGRESS
            self.started_at = datetime.utcnow()
            self.current_phase = PDCAPhase.PLAN
    
    def complete_phase(self, phase_result: PDCAPhaseResult) -> None:
        """Complete the current phase and advance to the next."""
        self.phase_results[phase_result.phase] = phase_result
        
        if phase_result.success:
            # Advance to next phase
            if self.current_phase == PDCAPhase.PLAN:
                self.current_phase = PDCAPhase.DO
            elif self.current_phase == PDCAPhase.DO:
                self.current_phase = PDCAPhase.CHECK
            elif self.current_phase == PDCAPhase.CHECK:
                self.current_phase = PDCAPhase.ACT
            elif self.current_phase == PDCAPhase.ACT:
                self.current_phase = PDCAPhase.COMPLETE
                self.complete_cycle()
        else:
            # Phase failed - cycle needs attention
            self.status = CycleStatus.FAILED
    
    def complete_cycle(self) -> None:
        """Complete the entire PDCA cycle."""
        self.status = CycleStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.current_phase = PDCAPhase.COMPLETE
    
    def get_duration(self) -> Optional[timedelta]:
        """Get the total duration of the cycle."""
        if self.started_at is None:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    def get_phase_duration(self, phase: PDCAPhase) -> Optional[timedelta]:
        """Get the duration of a specific phase."""
        if phase not in self.phase_results:
            return None
        
        return timedelta(seconds=self.phase_results[phase].duration_seconds)
    
    def is_complete(self) -> bool:
        """Check if the cycle is complete."""
        return self.status == CycleStatus.COMPLETED
    
    def is_successful(self) -> bool:
        """Check if the cycle completed successfully."""
        return (self.is_complete() and 
                all(result.success for result in self.phase_results.values()))
    
    def get_all_lessons_learned(self) -> List[str]:
        """Get all lessons learned across all phases."""
        lessons = []
        for result in self.phase_results.values():
            lessons.extend(result.lessons_learned)
        return lessons
    
    def add_objective(self, objective: str) -> None:
        """Add an objective to the cycle."""
        if objective and objective not in self.objectives:
            self.objectives.append(objective)
    
    def add_success_criterion(self, criterion: str) -> None:
        """Add a success criterion."""
        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)
    
    def record_outcome(self, outcome: str) -> None:
        """Record an actual outcome."""
        if outcome and outcome not in self.actual_outcomes:
            self.actual_outcomes.append(outcome)
    
    def identify_improvement(self, improvement: str) -> None:
        """Identify an improvement opportunity."""
        if improvement and improvement not in self.improvements_identified:
            self.improvements_identified.append(improvement)
    
    def recommend_for_next_cycle(self, recommendation: str) -> None:
        """Add a recommendation for the next cycle."""
        if recommendation and recommendation not in self.next_cycle_recommendations:
            self.next_cycle_recommendations.append(recommendation)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the cycle."""
        return {
            'cycle_id': self.cycle_id,
            'title': self.title,
            'status': self.status.value,
            'current_phase': self.current_phase.value,
            'duration_seconds': self.get_duration().total_seconds() if self.get_duration() else None,
            'phases_completed': len(self.phase_results),
            'is_successful': self.is_successful(),
            'objectives_count': len(self.objectives),
            'outcomes_count': len(self.actual_outcomes),
            'improvements_identified': len(self.improvements_identified),
            'lessons_learned_count': len(self.get_all_lessons_learned()),
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class PDCACore(ReflectiveModule):
    """
    Core PDCA cycle management interface for systematic continuous improvement.
    
    This class provides the foundational interface for managing Plan-Do-Check-Act
    cycles in the Beast Mode framework, enabling systematic continuous improvement
    rather than ad-hoc development approaches.
    
    Key Capabilities:
    - Systematic PDCA cycle creation and management
    - Phase transition validation and tracking
    - Continuous improvement identification and documentation
    - Performance measurement and optimization
    - Integration with other Beast Mode components
    """
    
    def __init__(self):
        """Initialize the PDCA core interface."""
        super().__init__()
        self._active_cycles: Dict[str, PDCACycle] = {}
        self._completed_cycles: Dict[str, PDCACycle] = {}
        self._cycle_templates: Dict[str, Dict[str, Any]] = {}
        self._performance_metrics = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'average_cycle_duration': 0.0,
            'improvement_rate': 0.0
        }
        self._load_default_templates()
    
    def get_module_status(self) -> ModuleStatus:
        """Get the current status of the PDCA core."""
        if len(self._active_cycles) > 10:  # Too many active cycles
            return ModuleStatus.DEGRADED
        
        failed_cycles = sum(1 for cycle in self._active_cycles.values() 
                          if cycle.status == CycleStatus.FAILED)
        
        if failed_cycles > len(self._active_cycles) * 0.3:  # >30% failed
            return ModuleStatus.UNHEALTHY
        
        return ModuleStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """Check if the PDCA core is healthy."""
        return self.get_module_status() == ModuleStatus.HEALTHY
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get detailed health indicators for the PDCA core."""
        indicators = []
        
        # Active cycles health
        active_count = len(self._active_cycles)
        if active_count <= 5:
            status = "healthy"
            message = f"Manageable active cycles: {active_count}"
        elif active_count <= 10:
            status = "degraded"
            message = f"High active cycles: {active_count}"
        else:
            status = "unhealthy"
            message = f"Too many active cycles: {active_count}"
        
        indicators.append(HealthIndicator(
            name="active_cycles",
            status=status,
            message=message,
            details={'active_count': active_count}
        ))
        
        # Success rate health
        total_cycles = self._performance_metrics['total_cycles']
        if total_cycles > 0:
            success_rate = self._performance_metrics['successful_cycles'] / total_cycles
            if success_rate >= 0.8:
                status = "healthy"
                message = f"High success rate: {success_rate:.1%}"
            elif success_rate >= 0.6:
                status = "degraded"
                message = f"Moderate success rate: {success_rate:.1%}"
            else:
                status = "unhealthy"
                message = f"Low success rate: {success_rate:.1%}"
        else:
            status = "healthy"
            message = "No cycles completed yet"
        
        indicators.append(HealthIndicator(
            name="success_rate",
            status=status,
            message=message,
            details={'total_cycles': total_cycles}
        ))
        
        # Performance health
        avg_duration = self._performance_metrics['average_cycle_duration']
        if avg_duration <= 3600:  # 1 hour
            status = "healthy"
            message = f"Fast cycle completion: {avg_duration/60:.1f} minutes"
        elif avg_duration <= 7200:  # 2 hours
            status = "degraded"
            message = f"Acceptable cycle duration: {avg_duration/60:.1f} minutes"
        else:
            status = "unhealthy"
            message = f"Slow cycle completion: {avg_duration/60:.1f} minutes"
        
        indicators.append(HealthIndicator(
            name="performance",
            status=status,
            message=message,
            details=self._performance_metrics.copy()
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information about the PDCA core."""
        return {
            'module_type': 'PDCACore',
            'active_cycles': len(self._active_cycles),
            'completed_cycles': len(self._completed_cycles),
            'available_templates': len(self._cycle_templates),
            'performance_metrics': self._performance_metrics.copy(),
            'capabilities': [
                'Systematic PDCA cycle management',
                'Phase transition validation',
                'Continuous improvement tracking',
                'Performance measurement',
                'Template-based cycle creation'
            ],
            'cycle_templates': list(self._cycle_templates.keys()),
            'uptime_seconds': self.get_uptime()
        }
    
    def create_cycle(self, title: str, description: str = "", 
                    template_name: Optional[str] = None) -> PDCACycle:
        """
        Create a new PDCA cycle.
        
        Args:
            title: Title of the cycle
            description: Description of what the cycle aims to achieve
            template_name: Optional template to use for cycle creation
            
        Returns:
            PDCACycle: The created cycle
        """
        cycle = PDCACycle(title=title, description=description)
        
        # Apply template if specified
        if template_name and template_name in self._cycle_templates:
            template = self._cycle_templates[template_name]
            cycle.objectives.extend(template.get('objectives', []))
            cycle.success_criteria.extend(template.get('success_criteria', []))
            cycle.context.update(template.get('context', {}))
            cycle.tags.extend(template.get('tags', []))
        
        self._active_cycles[cycle.cycle_id] = cycle
        return cycle
    
    def start_cycle(self, cycle_id: str) -> bool:
        """
        Start a PDCA cycle.
        
        Args:
            cycle_id: ID of the cycle to start
            
        Returns:
            bool: True if cycle was started successfully
        """
        if cycle_id not in self._active_cycles:
            return False
        
        cycle = self._active_cycles[cycle_id]
        cycle.start_cycle()
        return True
    
    def execute_plan_phase(self, cycle_id: str, 
                          plan_executor: Callable[[PDCACycle], PDCAPhaseResult]) -> PDCAPhaseResult:
        """
        Execute the Plan phase of a PDCA cycle.
        
        Args:
            cycle_id: ID of the cycle
            plan_executor: Function to execute the planning phase
            
        Returns:
            PDCAPhaseResult: Result of the plan phase
        """
        if cycle_id not in self._active_cycles:
            return PDCAPhaseResult(
                phase=PDCAPhase.PLAN,
                success=False,
                message="Cycle not found"
            )
        
        cycle = self._active_cycles[cycle_id]
        
        if cycle.current_phase != PDCAPhase.PLAN:
            return PDCAPhaseResult(
                phase=PDCAPhase.PLAN,
                success=False,
                message=f"Cycle is in {cycle.current_phase.value} phase, not PLAN"
            )
        
        start_time = time.time()
        
        try:
            result = plan_executor(cycle)
            result.duration_seconds = time.time() - start_time
            cycle.complete_phase(result)
            return result
            
        except Exception as e:
            result = PDCAPhaseResult(
                phase=PDCAPhase.PLAN,
                success=False,
                message=f"Plan phase failed: {str(e)}",
                details={'error': str(e)},
                duration_seconds=time.time() - start_time
            )
            cycle.complete_phase(result)
            return result
    
    def execute_do_phase(self, cycle_id: str,
                        do_executor: Callable[[PDCACycle], PDCAPhaseResult]) -> PDCAPhaseResult:
        """
        Execute the Do phase of a PDCA cycle.
        
        Args:
            cycle_id: ID of the cycle
            do_executor: Function to execute the do phase
            
        Returns:
            PDCAPhaseResult: Result of the do phase
        """
        return self._execute_phase(cycle_id, PDCAPhase.DO, do_executor)
    
    def execute_check_phase(self, cycle_id: str,
                           check_executor: Callable[[PDCACycle], PDCAPhaseResult]) -> PDCAPhaseResult:
        """
        Execute the Check phase of a PDCA cycle.
        
        Args:
            cycle_id: ID of the cycle
            check_executor: Function to execute the check phase
            
        Returns:
            PDCAPhaseResult: Result of the check phase
        """
        return self._execute_phase(cycle_id, PDCAPhase.CHECK, check_executor)
    
    def execute_act_phase(self, cycle_id: str,
                         act_executor: Callable[[PDCACycle], PDCAPhaseResult]) -> PDCAPhaseResult:
        """
        Execute the Act phase of a PDCA cycle.
        
        Args:
            cycle_id: ID of the cycle
            act_executor: Function to execute the act phase
            
        Returns:
            PDCAPhaseResult: Result of the act phase
        """
        result = self._execute_phase(cycle_id, PDCAPhase.ACT, act_executor)
        
        # If Act phase completed successfully, finalize the cycle
        if result.success and cycle_id in self._active_cycles:
            cycle = self._active_cycles[cycle_id]
            if cycle.is_complete():
                self._finalize_cycle(cycle_id)
        
        return result
    
    def get_cycle(self, cycle_id: str) -> Optional[PDCACycle]:
        """
        Get a cycle by ID.
        
        Args:
            cycle_id: ID of the cycle
            
        Returns:
            Optional[PDCACycle]: The cycle if found
        """
        if cycle_id in self._active_cycles:
            return self._active_cycles[cycle_id]
        elif cycle_id in self._completed_cycles:
            return self._completed_cycles[cycle_id]
        return None
    
    def list_active_cycles(self) -> List[PDCACycle]:
        """Get all active cycles."""
        return list(self._active_cycles.values())
    
    def list_completed_cycles(self) -> List[PDCACycle]:
        """Get all completed cycles."""
        return list(self._completed_cycles.values())
    
    def cancel_cycle(self, cycle_id: str, reason: str = "") -> bool:
        """
        Cancel an active cycle.
        
        Args:
            cycle_id: ID of the cycle to cancel
            reason: Reason for cancellation
            
        Returns:
            bool: True if cycle was cancelled
        """
        if cycle_id not in self._active_cycles:
            return False
        
        cycle = self._active_cycles[cycle_id]
        cycle.status = CycleStatus.CANCELLED
        cycle.context['cancellation_reason'] = reason
        cycle.context['cancelled_at'] = datetime.utcnow().isoformat()
        
        # Move to completed cycles
        self._completed_cycles[cycle_id] = cycle
        del self._active_cycles[cycle_id]
        
        return True
    
    def get_improvement_insights(self) -> Dict[str, Any]:
        """
        Get insights from completed cycles for continuous improvement.
        
        Returns:
            Dict[str, Any]: Improvement insights and recommendations
        """
        if not self._completed_cycles:
            return {
                'total_cycles': 0,
                'insights': [],
                'recommendations': []
            }
        
        cycles = list(self._completed_cycles.values())
        
        # Analyze patterns
        successful_cycles = [c for c in cycles if c.is_successful()]
        failed_cycles = [c for c in cycles if c.status == CycleStatus.FAILED]
        
        # Collect all lessons learned
        all_lessons = []
        for cycle in cycles:
            all_lessons.extend(cycle.get_all_lessons_learned())
        
        # Analyze durations
        durations = [c.get_duration().total_seconds() for c in cycles if c.get_duration()]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Generate insights
        insights = []
        recommendations = []
        
        if len(successful_cycles) > 0:
            success_rate = len(successful_cycles) / len(cycles)
            insights.append(f"Success rate: {success_rate:.1%}")
            
            if success_rate < 0.7:
                recommendations.append("Focus on improving cycle planning and execution")
        
        if avg_duration > 0:
            insights.append(f"Average cycle duration: {avg_duration/60:.1f} minutes")
            
            if avg_duration > 7200:  # > 2 hours
                recommendations.append("Consider breaking down cycles into smaller iterations")
        
        if len(failed_cycles) > 0:
            insights.append(f"Failed cycles: {len(failed_cycles)}")
            recommendations.append("Analyze failed cycles for common patterns")
        
        # Most common lessons
        lesson_counts = {}
        for lesson in all_lessons:
            lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1
        
        common_lessons = sorted(lesson_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_cycles': len(cycles),
            'successful_cycles': len(successful_cycles),
            'failed_cycles': len(failed_cycles),
            'average_duration_seconds': avg_duration,
            'insights': insights,
            'recommendations': recommendations,
            'common_lessons': [lesson for lesson, count in common_lessons],
            'performance_metrics': self._performance_metrics.copy()
        }
    
    def _execute_phase(self, cycle_id: str, expected_phase: PDCAPhase,
                      executor: Callable[[PDCACycle], PDCAPhaseResult]) -> PDCAPhaseResult:
        """Execute a specific phase of a PDCA cycle."""
        if cycle_id not in self._active_cycles:
            return PDCAPhaseResult(
                phase=expected_phase,
                success=False,
                message="Cycle not found"
            )
        
        cycle = self._active_cycles[cycle_id]
        
        if cycle.current_phase != expected_phase:
            return PDCAPhaseResult(
                phase=expected_phase,
                success=False,
                message=f"Cycle is in {cycle.current_phase.value} phase, not {expected_phase.value}"
            )
        
        start_time = time.time()
        
        try:
            result = executor(cycle)
            result.duration_seconds = time.time() - start_time
            cycle.complete_phase(result)
            return result
            
        except Exception as e:
            result = PDCAPhaseResult(
                phase=expected_phase,
                success=False,
                message=f"{expected_phase.value} phase failed: {str(e)}",
                details={'error': str(e)},
                duration_seconds=time.time() - start_time
            )
            cycle.complete_phase(result)
            return result
    
    def _finalize_cycle(self, cycle_id: str) -> None:
        """Finalize a completed cycle and update metrics."""
        if cycle_id not in self._active_cycles:
            return
        
        cycle = self._active_cycles[cycle_id]
        
        # Update performance metrics
        self._performance_metrics['total_cycles'] += 1
        
        if cycle.is_successful():
            self._performance_metrics['successful_cycles'] += 1
        
        # Update average duration
        if cycle.get_duration():
            duration = cycle.get_duration().total_seconds()
            total_cycles = self._performance_metrics['total_cycles']
            current_avg = self._performance_metrics['average_cycle_duration']
            
            self._performance_metrics['average_cycle_duration'] = (
                (current_avg * (total_cycles - 1) + duration) / total_cycles
            )
        
        # Calculate improvement rate (cycles with improvements identified)
        if cycle.improvements_identified:
            cycles_with_improvements = sum(
                1 for c in self._completed_cycles.values() 
                if c.improvements_identified
            ) + 1  # +1 for current cycle
            
            total_completed = len(self._completed_cycles) + 1
            self._performance_metrics['improvement_rate'] = cycles_with_improvements / total_completed
        
        # Move to completed cycles
        self._completed_cycles[cycle_id] = cycle
        del self._active_cycles[cycle_id]
    
    def _load_default_templates(self) -> None:
        """Load default PDCA cycle templates."""
        self._cycle_templates = {
            'development_task': {
                'objectives': [
                    'Complete development task systematically',
                    'Ensure quality and maintainability',
                    'Document lessons learned'
                ],
                'success_criteria': [
                    'Task completed within estimated time',
                    'Code passes all tests',
                    'Documentation updated',
                    'No regressions introduced'
                ],
                'context': {'template_type': 'development'},
                'tags': ['development', 'systematic']
            },
            'problem_solving': {
                'objectives': [
                    'Identify root cause systematically',
                    'Implement effective solution',
                    'Prevent recurrence'
                ],
                'success_criteria': [
                    'Root cause identified and validated',
                    'Solution implemented and tested',
                    'Prevention measures in place',
                    'Documentation updated'
                ],
                'context': {'template_type': 'problem_solving'},
                'tags': ['problem_solving', 'rca', 'systematic']
            },
            'process_improvement': {
                'objectives': [
                    'Analyze current process systematically',
                    'Identify improvement opportunities',
                    'Implement and validate improvements'
                ],
                'success_criteria': [
                    'Process analyzed and documented',
                    'Improvements identified and prioritized',
                    'Changes implemented and measured',
                    'Results validated and documented'
                ],
                'context': {'template_type': 'process_improvement'},
                'tags': ['process', 'improvement', 'systematic']
            }
        }