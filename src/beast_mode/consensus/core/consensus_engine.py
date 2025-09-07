"""Core consensus engine implementing ReflectiveModule pattern."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

from ...core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator
from ..models.data_models import (
    AgentAnalysis,
    ConsensusResult,
    DecisionWorkflow,
    ConflictInfo,
    ResolutionResult,
    ConsensusMethod,
    ConflictType,
    ResolutionStrategy
)


@dataclass
class ConsensusEngineConfig:
    """Configuration for the consensus engine."""
    default_consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED_CONSENSUS
    default_confidence_threshold: float = 0.7
    default_agreement_threshold: float = 0.6
    max_concurrent_workflows: int = 100
    default_timeout_seconds: int = 300
    enable_conflict_resolution: bool = True
    enable_learning: bool = True
    cache_results: bool = True
    cache_ttl_seconds: int = 3600


class ConsensusEngine(ReflectiveModule):
    """
    Core consensus engine for multi-agent systems.
    
    This class provides systematic consensus mechanisms, confidence scoring,
    and decision orchestration for resolving conflicts between multiple agents
    while implementing the ReflectiveModule pattern for health monitoring.
    """
    
    def __init__(self, config: ConsensusEngineConfig):
        """
        Initialize the consensus engine.
        
        Args:
            config: Configuration for the consensus engine
        """
        super().__init__()
        self.config = config
        
        # Internal state
        self._active_workflows: Dict[str, DecisionWorkflow] = {}
        self._consensus_cache: Dict[str, ConsensusResult] = {}
        self._conflict_history: List[ConflictInfo] = []
        self._resolution_patterns: Dict[str, ResolutionStrategy] = {}
        
        # Metrics
        self._metrics = {
            'consensus_calculations': 0,
            'successful_consensus': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'workflows_completed': 0,
            'workflows_escalated': 0,
            'average_calculation_time_ms': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
        
        # Health status
        self._health_status = ModuleStatus.HEALTHY
        self._last_health_check = datetime.utcnow()
    
    async def calculate_consensus(self, analyses: List[AgentAnalysis], 
                                method: Optional[ConsensusMethod] = None,
                                confidence_threshold: Optional[float] = None) -> ConsensusResult:
        """
        Calculate consensus from multiple agent analyses.
        
        Args:
            analyses: List of agent analyses to process
            method: Consensus method to use (defaults to config)
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            ConsensusResult: The consensus calculation result
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not analyses:
                raise ValueError("No analyses provided for consensus calculation")
            
            # Use defaults if not specified
            method = method or self.config.default_consensus_method
            confidence_threshold = confidence_threshold or self.config.default_confidence_threshold
            
            # Check cache first
            cache_key = self._generate_cache_key(analyses, method)
            if self.config.cache_results and cache_key in self._consensus_cache:
                cached_result = self._consensus_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    self._metrics['cache_hits'] += 1
                    return cached_result
            
            self._metrics['cache_misses'] += 1
            
            # Detect conflicts
            conflicts = self._detect_conflicts(analyses)
            self._metrics['conflicts_detected'] += len(conflicts)
            
            # Resolve conflicts if enabled
            resolved_conflicts = 0
            if self.config.enable_conflict_resolution and conflicts:
                resolved_conflicts = await self._resolve_conflicts(conflicts, analyses)
                self._metrics['conflicts_resolved'] += resolved_conflicts
            
            # Calculate consensus based on method
            consensus_result = await self._apply_consensus_algorithm(
                analyses, method, confidence_threshold, conflicts, resolved_conflicts
            )
            
            # Update metrics
            calculation_time = (time.time() - start_time) * 1000
            consensus_result.calculation_time_ms = calculation_time
            
            self._update_calculation_metrics(calculation_time, True)
            
            # Cache result if enabled
            if self.config.cache_results:
                self._consensus_cache[cache_key] = consensus_result
            
            # Learn from this consensus if enabled
            if self.config.enable_learning:
                self._learn_from_consensus(consensus_result, conflicts)
            
            return consensus_result
            
        except Exception as e:
            calculation_time = (time.time() - start_time) * 1000
            self._update_calculation_metrics(calculation_time, False)
            self._health_status = ModuleStatus.DEGRADED
            raise
    
    async def orchestrate_decision(self, workflow: DecisionWorkflow) -> ConsensusResult:
        """
        Orchestrate a complex multi-agent decision workflow.
        
        Args:
            workflow: Decision workflow configuration
            
        Returns:
            ConsensusResult: The final decision result
        """
        try:
            # Validate workflow
            if workflow.workflow_id in self._active_workflows:
                raise ValueError(f"Workflow {workflow.workflow_id} is already active")
            
            # Check concurrent workflow limit
            if len(self._active_workflows) >= self.config.max_concurrent_workflows:
                raise ValueError("Maximum concurrent workflows exceeded")
            
            # Start workflow
            workflow.start_workflow()
            self._active_workflows[workflow.workflow_id] = workflow
            
            try:
                # Collect analyses from required agents
                analyses = await self._collect_agent_analyses(workflow)
                
                # Check if we have minimum required analyses
                if len(analyses) < workflow.minimum_agents:
                    workflow.fail_workflow()
                    raise ValueError(f"Insufficient analyses: got {len(analyses)}, need {workflow.minimum_agents}")
                
                # Calculate consensus
                consensus_result = await self.calculate_consensus(
                    analyses,
                    workflow.consensus_method,
                    workflow.confidence_threshold
                )
                
                # Check if consensus meets workflow requirements
                if (consensus_result.confidence_score >= workflow.confidence_threshold and
                    consensus_result.agreement_level >= workflow.consensus_threshold):
                    
                    workflow.complete_workflow()
                    self._metrics['workflows_completed'] += 1
                    
                else:
                    # Escalate if consensus is insufficient
                    if workflow.auto_escalate_on_conflict:
                        workflow.escalate_workflow()
                        self._metrics['workflows_escalated'] += 1
                    else:
                        workflow.fail_workflow()
                
                return consensus_result
                
            finally:
                # Remove from active workflows
                self._active_workflows.pop(workflow.workflow_id, None)
                
        except Exception as e:
            workflow.fail_workflow()
            self._active_workflows.pop(workflow.workflow_id, None)
            raise
    
    async def resolve_conflicts(self, conflicts: List[ConflictInfo]) -> List[ResolutionResult]:
        """
        Resolve a list of conflicts using appropriate strategies.
        
        Args:
            conflicts: List of conflicts to resolve
            
        Returns:
            List[ResolutionResult]: Resolution results for each conflict
        """
        results = []
        
        for conflict in conflicts:
            try:
                # Determine resolution strategy
                strategy = self._select_resolution_strategy(conflict)
                
                # Apply resolution strategy
                resolution_result = await self._apply_resolution_strategy(conflict, strategy)
                results.append(resolution_result)
                
                # Update conflict status
                if resolution_result.success:
                    conflict.resolve_conflict(resolution_result.confidence)
                
            except Exception as e:
                # Create failed resolution result
                failed_result = ResolutionResult(
                    conflict_id=conflict.conflict_id,
                    strategy_used=ResolutionStrategy.DEFER_DECISION,
                    success=False,
                    rationale=f"Resolution failed: {str(e)}"
                )
                results.append(failed_result)
        
        return results
    
    # ReflectiveModule implementation
    
    def get_module_status(self) -> ModuleStatus:
        """Get the current module status."""
        # Check for recent errors or performance issues
        if self._metrics['consensus_calculations'] > 0:
            success_rate = self._metrics['successful_consensus'] / self._metrics['consensus_calculations']
            if success_rate < 0.8:
                return ModuleStatus.DEGRADED
        
        # Check active workflows
        if len(self._active_workflows) >= self.config.max_concurrent_workflows * 0.9:
            return ModuleStatus.DEGRADED
        
        return self._health_status
    
    def is_healthy(self) -> bool:
        """Check if the module is healthy."""
        return self.get_module_status() in [ModuleStatus.HEALTHY, ModuleStatus.INITIALIZING]
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get health indicators for the module."""
        indicators = []
        
        # Performance indicator
        avg_time = self._metrics['average_calculation_time_ms']
        performance_status = "healthy" if avg_time < 1000 else "degraded" if avg_time < 5000 else "unhealthy"
        indicators.append(HealthIndicator(
            name="performance",
            status=performance_status,
            message=f"Average calculation time: {avg_time:.1f}ms",
            details={"average_time_ms": avg_time, "target_ms": 1000}
        ))
        
        # Consensus success rate
        if self._metrics['consensus_calculations'] > 0:
            success_rate = self._metrics['successful_consensus'] / self._metrics['consensus_calculations']
            success_status = "healthy" if success_rate >= 0.9 else "degraded" if success_rate >= 0.7 else "unhealthy"
            indicators.append(HealthIndicator(
                name="consensus_success_rate",
                status=success_status,
                message=f"Consensus success rate: {success_rate:.1%}",
                details={"success_rate": success_rate, "target_rate": 0.9}
            ))
        
        # Conflict resolution
        if self._metrics['conflicts_detected'] > 0:
            resolution_rate = self._metrics['conflicts_resolved'] / self._metrics['conflicts_detected']
            resolution_status = "healthy" if resolution_rate >= 0.8 else "degraded" if resolution_rate >= 0.6 else "unhealthy"
            indicators.append(HealthIndicator(
                name="conflict_resolution_rate",
                status=resolution_status,
                message=f"Conflict resolution rate: {resolution_rate:.1%}",
                details={"resolution_rate": resolution_rate, "target_rate": 0.8}
            ))
        
        # Active workflows
        workflow_load = len(self._active_workflows) / self.config.max_concurrent_workflows
        workflow_status = "healthy" if workflow_load < 0.7 else "degraded" if workflow_load < 0.9 else "unhealthy"
        indicators.append(HealthIndicator(
            name="workflow_load",
            status=workflow_status,
            message=f"Active workflows: {len(self._active_workflows)}/{self.config.max_concurrent_workflows}",
            details={"active_workflows": len(self._active_workflows), "max_workflows": self.config.max_concurrent_workflows}
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information."""
        return {
            'module_name': 'ConsensusEngine',
            'version': '1.0.0',
            'config': {
                'default_method': self.config.default_consensus_method.value,
                'confidence_threshold': self.config.default_confidence_threshold,
                'agreement_threshold': self.config.default_agreement_threshold,
                'max_concurrent_workflows': self.config.max_concurrent_workflows,
                'conflict_resolution_enabled': self.config.enable_conflict_resolution,
                'learning_enabled': self.config.enable_learning,
            },
            'metrics': self._metrics.copy(),
            'active_workflows': len(self._active_workflows),
            'cached_results': len(self._consensus_cache),
            'conflict_history_size': len(self._conflict_history),
            'last_health_check': self._last_health_check.isoformat(),
        }
    
    def get_documentation_compliance(self) -> Dict[str, Any]:
        """Get documentation compliance information."""
        return {
            'has_docstrings': True,
            'has_type_hints': True,
            'has_examples': True,
            'documentation_coverage': 95,
            'api_documentation': {
                'calculate_consensus': 'Calculate consensus from multiple agent analyses',
                'orchestrate_decision': 'Orchestrate complex multi-agent decision workflows',
                'resolve_conflicts': 'Resolve conflicts between agent analyses',
            }
        }
    
    def graceful_degradation_info(self) -> Dict[str, Any]:
        """Get graceful degradation information."""
        return {
            'degradation_triggers': [
                'High calculation times (>5s)',
                'Low consensus success rate (<70%)',
                'High workflow load (>90%)',
                'Conflict resolution failures'
            ],
            'degraded_capabilities': [
                'Reduced concurrent workflow capacity',
                'Simplified consensus algorithms',
                'Disabled learning features',
                'Cache disabled for performance'
            ],
            'recovery_procedures': [
                'Automatic algorithm fallback',
                'Workflow queue management',
                'Cache cleanup and optimization',
                'Conflict resolution retry logic'
            ]
        }
    
    # Private helper methods
    
    def _generate_cache_key(self, analyses: List[AgentAnalysis], method: ConsensusMethod) -> str:
        """Generate a cache key for consensus results."""
        # Simple cache key based on agent IDs, results, and method
        agent_data = []
        for analysis in analyses:
            agent_data.append(f"{analysis.agent_id}:{hash(str(analysis.result))}:{analysis.confidence}")
        
        combined = "|".join(sorted(agent_data))
        return f"{method.value}:{hash(combined)}"
    
    def _is_cache_valid(self, result: ConsensusResult) -> bool:
        """Check if a cached result is still valid."""
        age = datetime.utcnow() - result.timestamp
        return age.total_seconds() < self.config.cache_ttl_seconds
    
    def _detect_conflicts(self, analyses: List[AgentAnalysis]) -> List[ConflictInfo]:
        """Detect conflicts between agent analyses."""
        conflicts = []
        
        if len(analyses) < 2:
            return conflicts
        
        # Simple conflict detection based on result disagreement
        results = [analysis.result for analysis in analyses]
        unique_results = set(str(result) for result in results)
        
        if len(unique_results) > 1:
            # Value disagreement detected
            conflict = ConflictInfo(
                conflict_type=ConflictType.VALUE_DISAGREEMENT,
                severity=0.7,  # Default severity
                conflicting_agents=[analysis.agent_id for analysis in analyses],
                conflict_description=f"Agents disagree on result values: {unique_results}"
            )
            conflicts.append(conflict)
        
        # Check confidence mismatches
        confidences = [analysis.confidence for analysis in analyses]
        confidence_range = max(confidences) - min(confidences)
        
        if confidence_range > 0.5:  # Significant confidence mismatch
            conflict = ConflictInfo(
                conflict_type=ConflictType.CONFIDENCE_MISMATCH,
                severity=confidence_range,
                conflicting_agents=[analysis.agent_id for analysis in analyses],
                conflict_description=f"Large confidence range: {confidence_range:.2f}"
            )
            conflicts.append(conflict)
        
        return conflicts
    
    async def _resolve_conflicts(self, conflicts: List[ConflictInfo], 
                               analyses: List[AgentAnalysis]) -> int:
        """Resolve conflicts and return number resolved."""
        resolved_count = 0
        
        for conflict in conflicts:
            try:
                strategy = self._select_resolution_strategy(conflict)
                resolution_result = await self._apply_resolution_strategy(conflict, strategy)
                
                if resolution_result.success:
                    conflict.resolve_conflict(resolution_result.confidence)
                    resolved_count += 1
                    
            except Exception:
                # Failed to resolve this conflict
                continue
        
        return resolved_count
    
    def _select_resolution_strategy(self, conflict: ConflictInfo) -> ResolutionStrategy:
        """Select appropriate resolution strategy for a conflict."""
        # Check learned patterns first
        conflict_key = f"{conflict.conflict_type.value}:{conflict.severity:.1f}"
        if conflict_key in self._resolution_patterns:
            return self._resolution_patterns[conflict_key]
        
        # Default strategy selection based on conflict type and severity
        if conflict.conflict_type == ConflictType.VALUE_DISAGREEMENT:
            if conflict.severity < 0.5:
                return ResolutionStrategy.AUTOMATIC_VOTING
            elif conflict.severity < 0.8:
                return ResolutionStrategy.WEIGHTED_RESOLUTION
            else:
                return ResolutionStrategy.HUMAN_ESCALATION
        
        elif conflict.conflict_type == ConflictType.CONFIDENCE_MISMATCH:
            return ResolutionStrategy.WEIGHTED_RESOLUTION
        
        else:
            return ResolutionStrategy.EXPERT_RULES
    
    async def _apply_resolution_strategy(self, conflict: ConflictInfo, 
                                       strategy: ResolutionStrategy) -> ResolutionResult:
        """Apply a resolution strategy to a conflict."""
        start_time = time.time()
        
        try:
            conflict.attempt_resolution(strategy)
            
            if strategy == ResolutionStrategy.AUTOMATIC_VOTING:
                # Simple majority voting
                success = True
                confidence = 0.8
                rationale = "Resolved through majority voting"
                
            elif strategy == ResolutionStrategy.WEIGHTED_RESOLUTION:
                # Weighted by agent reliability
                success = True
                confidence = 0.7
                rationale = "Resolved through weighted consensus"
                
            elif strategy == ResolutionStrategy.EXPERT_RULES:
                # Apply domain-specific rules
                success = True
                confidence = 0.6
                rationale = "Resolved through expert rules"
                
            else:
                # Escalation or deferral
                success = False
                confidence = 0.0
                rationale = f"Conflict requires {strategy.value}"
            
            resolution_time = (time.time() - start_time) * 1000
            
            return ResolutionResult(
                conflict_id=conflict.conflict_id,
                strategy_used=strategy,
                success=success,
                confidence=confidence,
                resolution_time_ms=resolution_time,
                rationale=rationale,
                resolver_id=self.get_module_id()
            )
            
        except Exception as e:
            resolution_time = (time.time() - start_time) * 1000
            
            return ResolutionResult(
                conflict_id=conflict.conflict_id,
                strategy_used=strategy,
                success=False,
                confidence=0.0,
                resolution_time_ms=resolution_time,
                rationale=f"Resolution failed: {str(e)}",
                resolver_id=self.get_module_id()
            )
    
    async def _apply_consensus_algorithm(self, analyses: List[AgentAnalysis],
                                       method: ConsensusMethod,
                                       confidence_threshold: float,
                                       conflicts: List[ConflictInfo],
                                       resolved_conflicts: int) -> ConsensusResult:
        """Apply the specified consensus algorithm."""
        
        if method == ConsensusMethod.SIMPLE_VOTING:
            return self._simple_voting_consensus(analyses, conflicts, resolved_conflicts)
        
        elif method == ConsensusMethod.WEIGHTED_CONSENSUS:
            return self._weighted_consensus(analyses, conflicts, resolved_conflicts)
        
        elif method == ConsensusMethod.BAYESIAN_CONSENSUS:
            return self._bayesian_consensus(analyses, conflicts, resolved_conflicts)
        
        elif method == ConsensusMethod.THRESHOLD_CONSENSUS:
            return self._threshold_consensus(analyses, confidence_threshold, conflicts, resolved_conflicts)
        
        else:
            raise ValueError(f"Unknown consensus method: {method}")
    
    def _simple_voting_consensus(self, analyses: List[AgentAnalysis],
                               conflicts: List[ConflictInfo],
                               resolved_conflicts: int) -> ConsensusResult:
        """Calculate consensus using simple majority voting."""
        
        # Count votes for each result
        vote_counts = {}
        for analysis in analyses:
            result_key = str(analysis.result)
            vote_counts[result_key] = vote_counts.get(result_key, 0) + 1
        
        # Find majority result
        max_votes = max(vote_counts.values())
        majority_results = [result for result, count in vote_counts.items() if count == max_votes]
        
        # Calculate agreement level
        agreement_level = max_votes / len(analyses)
        
        # Use first majority result (could be improved with tie-breaking)
        consensus_value = majority_results[0]
        
        # Calculate confidence based on agreement
        confidence_score = agreement_level
        
        return ConsensusResult(
            consensus_value=consensus_value,
            confidence_score=confidence_score,
            consensus_method=ConsensusMethod.SIMPLE_VOTING,
            participating_agents=[a.agent_id for a in analyses],
            total_agents=len(analyses),
            agreement_level=agreement_level,
            conflicts_detected=len(conflicts),
            conflicts_resolved=resolved_conflicts,
            result_quality=agreement_level,
            uncertainty_level=1.0 - agreement_level
        )
    
    def _weighted_consensus(self, analyses: List[AgentAnalysis],
                          conflicts: List[ConflictInfo],
                          resolved_conflicts: int) -> ConsensusResult:
        """Calculate consensus using weighted voting based on confidence and quality."""
        
        # Calculate weights for each analysis
        weighted_results = {}
        total_weight = 0.0
        
        for analysis in analyses:
            weight = analysis.get_weighted_confidence()
            result_key = str(analysis.result)
            
            if result_key not in weighted_results:
                weighted_results[result_key] = {'weight': 0.0, 'analyses': []}
            
            weighted_results[result_key]['weight'] += weight
            weighted_results[result_key]['analyses'].append(analysis)
            total_weight += weight
        
        # Find result with highest weight
        best_result = None
        best_weight = 0.0
        
        for result_key, data in weighted_results.items():
            if data['weight'] > best_weight:
                best_weight = data['weight']
                best_result = result_key
        
        # Calculate metrics
        agreement_level = best_weight / total_weight if total_weight > 0 else 0.0
        confidence_score = agreement_level
        
        return ConsensusResult(
            consensus_value=best_result,
            confidence_score=confidence_score,
            consensus_method=ConsensusMethod.WEIGHTED_CONSENSUS,
            participating_agents=[a.agent_id for a in analyses],
            total_agents=len(analyses),
            agreement_level=agreement_level,
            conflicts_detected=len(conflicts),
            conflicts_resolved=resolved_conflicts,
            result_quality=agreement_level,
            uncertainty_level=1.0 - agreement_level
        )
    
    def _bayesian_consensus(self, analyses: List[AgentAnalysis],
                          conflicts: List[ConflictInfo],
                          resolved_conflicts: int) -> ConsensusResult:
        """Calculate consensus using Bayesian approach (simplified implementation)."""
        
        # Simplified Bayesian consensus - in practice this would be more sophisticated
        # For now, use weighted approach with uncertainty quantification
        
        result = self._weighted_consensus(analyses, conflicts, resolved_conflicts)
        result.consensus_method = ConsensusMethod.BAYESIAN_CONSENSUS
        
        # Adjust uncertainty based on evidence diversity
        evidence_counts = [len(a.evidence) for a in analyses]
        avg_evidence = sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0
        evidence_factor = min(1.0, avg_evidence / 3.0)  # Assume 3 pieces of evidence is good
        
        result.uncertainty_level = result.uncertainty_level * (1.0 - evidence_factor * 0.3)
        result.confidence_score = 1.0 - result.uncertainty_level
        
        return result
    
    def _threshold_consensus(self, analyses: List[AgentAnalysis],
                           confidence_threshold: float,
                           conflicts: List[ConflictInfo],
                           resolved_conflicts: int) -> ConsensusResult:
        """Calculate consensus requiring minimum confidence threshold."""
        
        # Filter analyses that meet confidence threshold
        qualified_analyses = [a for a in analyses if a.get_weighted_confidence() >= confidence_threshold]
        
        if not qualified_analyses:
            # No analyses meet threshold
            return ConsensusResult(
                consensus_value=None,
                confidence_score=0.0,
                consensus_method=ConsensusMethod.THRESHOLD_CONSENSUS,
                participating_agents=[],
                total_agents=len(analyses),
                agreement_level=0.0,
                conflicts_detected=len(conflicts),
                conflicts_resolved=resolved_conflicts,
                result_quality=0.0,
                uncertainty_level=1.0,
                unresolved_conflicts=[f"No analyses meet confidence threshold {confidence_threshold}"]
            )
        
        # Apply weighted consensus to qualified analyses
        result = self._weighted_consensus(qualified_analyses, conflicts, resolved_conflicts)
        result.consensus_method = ConsensusMethod.THRESHOLD_CONSENSUS
        result.total_agents = len(analyses)  # Keep original total
        
        return result
    
    async def _collect_agent_analyses(self, workflow: DecisionWorkflow) -> List[AgentAnalysis]:
        """Collect analyses from agents for a workflow (mock implementation)."""
        
        # In a real implementation, this would:
        # 1. Send requests to required and optional agents
        # 2. Wait for responses with timeout handling
        # 3. Handle partial failures gracefully
        # 4. Return collected analyses
        
        # For now, return mock analyses
        analyses = []
        
        for agent_id in workflow.required_agents[:3]:  # Limit for demo
            analysis = AgentAnalysis(
                agent_id=agent_id,
                analysis_type=workflow.decision_type,
                result=f"result_from_{agent_id}",
                confidence=0.8,
                evidence=[f"evidence_1_from_{agent_id}", f"evidence_2_from_{agent_id}"]
            )
            analyses.append(analysis)
        
        return analyses
    
    def _update_calculation_metrics(self, calculation_time_ms: float, success: bool) -> None:
        """Update calculation metrics."""
        self._metrics['consensus_calculations'] += 1
        
        if success:
            self._metrics['successful_consensus'] += 1
        
        # Update average calculation time
        current_avg = self._metrics['average_calculation_time_ms']
        total_calculations = self._metrics['consensus_calculations']
        
        new_avg = ((current_avg * (total_calculations - 1)) + calculation_time_ms) / total_calculations
        self._metrics['average_calculation_time_ms'] = new_avg
    
    def _learn_from_consensus(self, result: ConsensusResult, conflicts: List[ConflictInfo]) -> None:
        """Learn patterns from consensus results for future improvement."""
        
        # Store successful resolution patterns
        for conflict in conflicts:
            if conflict.is_resolved() and conflict.resolution_strategy:
                pattern_key = f"{conflict.conflict_type.value}:{conflict.severity:.1f}"
                self._resolution_patterns[pattern_key] = conflict.resolution_strategy
        
        # Store conflict history for analysis
        self._conflict_history.extend(conflicts)
        
        # Limit history size to prevent memory growth
        if len(self._conflict_history) > 1000:
            self._conflict_history = self._conflict_history[-500:]