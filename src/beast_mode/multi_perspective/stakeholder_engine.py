"""
Stakeholder-Driven Multi-Perspective Engine for Beast Mode Framework.

This module provides systematic multi-stakeholder analysis for decision
risk reduction, implementing the Beast Mode principle of comprehensive
perspective gathering over ad-hoc decision making.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import uuid

from ..core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator
from ..framework.data_models import (
    StakeholderType, StakeholderPerspective, DecisionContext, 
    MultiStakeholderAnalysis, ConfidenceLevel, RiskLevel, DecisionOutcome
)


@dataclass
class PerspectiveRequest:
    """Request for stakeholder perspective analysis."""
    stakeholder_type: StakeholderType
    decision_context: DecisionContext
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: str = "normal"  # low, normal, high, urgent
    requested_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    
    def is_overdue(self) -> bool:
        """Check if the request is overdue."""
        return self.deadline is not None and datetime.utcnow() > self.deadline


class StakeholderDrivenMultiPerspectiveEngine(ReflectiveModule):
    """
    Systematic multi-stakeholder analysis engine for decision risk reduction.
    
    This class orchestrates comprehensive perspective gathering from multiple
    stakeholders to reduce decision risk and improve outcomes through systematic
    analysis rather than ad-hoc decision making approaches.
    
    Key Capabilities:
    - Systematic stakeholder perspective collection and analysis
    - Decision risk reduction through comprehensive viewpoint synthesis
    - Confidence-based decision routing (<50% confidence triggers multi-perspective)
    - Stakeholder-specific analysis methods for each perspective type
    - Systematic conflict identification and resolution recommendations
    """
    
    def __init__(self):
        """Initialize the multi-perspective engine."""
        super().__init__()
        self._active_analyses: Dict[str, MultiStakeholderAnalysis] = {}
        self._completed_analyses: Dict[str, MultiStakeholderAnalysis] = {}
        self._perspective_requests: Dict[str, PerspectiveRequest] = {}
        self._stakeholder_capabilities = self._initialize_stakeholder_capabilities()
        self._performance_metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'average_analysis_time': 0.0,
            'risk_reduction_rate': 0.0,
            'consensus_achievement_rate': 0.0
        }
    
    def get_module_status(self) -> ModuleStatus:
        """Get the current status of the multi-perspective engine."""
        active_count = len(self._active_analyses)
        overdue_requests = sum(1 for req in self._perspective_requests.values() if req.is_overdue())
        
        if overdue_requests > active_count * 0.5:  # >50% overdue
            return ModuleStatus.UNHEALTHY
        
        if active_count > 20:  # Too many active analyses
            return ModuleStatus.DEGRADED
        
        return ModuleStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """Check if the multi-perspective engine is healthy."""
        return self.get_module_status() == ModuleStatus.HEALTHY
    
    def get_health_indicators(self) -> List[HealthIndicator]:
        """Get detailed health indicators for the multi-perspective engine."""
        indicators = []
        
        # Active analyses health
        active_count = len(self._active_analyses)
        if active_count <= 10:
            status = "healthy"
            message = f"Manageable active analyses: {active_count}"
        elif active_count <= 20:
            status = "degraded"
            message = f"High active analyses: {active_count}"
        else:
            status = "unhealthy"
            message = f"Too many active analyses: {active_count}"
        
        indicators.append(HealthIndicator(
            name="active_analyses",
            status=status,
            message=message,
            details={'active_count': active_count}
        ))
        
        # Request processing health
        overdue_count = sum(1 for req in self._perspective_requests.values() if req.is_overdue())
        total_requests = len(self._perspective_requests)
        
        if total_requests == 0 or overdue_count == 0:
            status = "healthy"
            message = "No overdue perspective requests"
        elif overdue_count <= total_requests * 0.2:  # <=20% overdue
            status = "degraded"
            message = f"Some overdue requests: {overdue_count}/{total_requests}"
        else:
            status = "unhealthy"
            message = f"Many overdue requests: {overdue_count}/{total_requests}"
        
        indicators.append(HealthIndicator(
            name="request_processing",
            status=status,
            message=message,
            details={'overdue_count': overdue_count, 'total_requests': total_requests}
        ))
        
        # Consensus achievement health
        consensus_rate = self._performance_metrics['consensus_achievement_rate']
        if consensus_rate >= 0.7:
            status = "healthy"
            message = f"High consensus rate: {consensus_rate:.1%}"
        elif consensus_rate >= 0.4:
            status = "degraded"
            message = f"Moderate consensus rate: {consensus_rate:.1%}"
        else:
            status = "unhealthy"
            message = f"Low consensus rate: {consensus_rate:.1%}"
        
        indicators.append(HealthIndicator(
            name="consensus_achievement",
            status=status,
            message=message,
            details=self._performance_metrics.copy()
        ))
        
        return indicators
    
    def get_operational_info(self) -> Dict[str, Any]:
        """Get operational information about the multi-perspective engine."""
        return {
            'module_type': 'StakeholderDrivenMultiPerspectiveEngine',
            'active_analyses': len(self._active_analyses),
            'completed_analyses': len(self._completed_analyses),
            'pending_requests': len(self._perspective_requests),
            'supported_stakeholders': [st.value for st in StakeholderType],
            'performance_metrics': self._performance_metrics.copy(),
            'capabilities': [
                'Multi-stakeholder perspective collection',
                'Decision risk reduction analysis',
                'Confidence-based decision routing',
                'Systematic conflict identification',
                'Consensus building and synthesis'
            ],
            'stakeholder_capabilities': {
                st.value: list(caps.keys()) 
                for st, caps in self._stakeholder_capabilities.items()
            },
            'uptime_seconds': self.get_uptime()
        }
    
    def analyze_low_percentage_decision(self, decision_context: DecisionContext,
                                      initial_confidence: float) -> MultiStakeholderAnalysis:
        """
        Analyze a decision with low confidence (<50%) using multi-stakeholder perspectives.
        
        This method is triggered when initial decision confidence is below 50%,
        implementing systematic risk reduction through comprehensive stakeholder analysis.
        
        Args:
            decision_context: Context of the decision requiring analysis
            initial_confidence: Initial confidence level (should be <0.5)
            
        Returns:
            MultiStakeholderAnalysis: Comprehensive multi-stakeholder analysis
        """
        analysis = MultiStakeholderAnalysis(decision_context=decision_context)
        
        # Determine required stakeholders based on decision type and context
        required_stakeholders = self._determine_required_stakeholders(decision_context)
        
        # Update decision context with required stakeholders
        for stakeholder in required_stakeholders:
            decision_context.require_stakeholder(stakeholder)
        
        # Generate perspectives for each required stakeholder
        for stakeholder_type in required_stakeholders:
            perspective = self._generate_stakeholder_perspective(stakeholder_type, decision_context)
            analysis.add_perspective(perspective)
        
        # Synthesize perspectives and complete analysis
        analysis.synthesize_perspectives()
        analysis.complete_analysis()
        
        # Store analysis
        self._active_analyses[analysis.analysis_id] = analysis
        
        # Update performance metrics
        self._update_performance_metrics(analysis)
        
        return analysis
    
    def beast_mode_perspective(self, decision_context: DecisionContext) -> StakeholderPerspective:
        """
        Generate Beast Mode framework perspective focusing on systematic superiority.
        
        Args:
            decision_context: Decision context to analyze
            
        Returns:
            StakeholderPerspective: Beast Mode perspective
        """
        perspective = StakeholderPerspective(
            stakeholder_type=StakeholderType.BEAST_MODE,
            viewpoint="Systematic approach evaluation for superior outcomes",
            analyst="BeastModeEngine"
        )
        
        # Analyze from Beast Mode systematic superiority viewpoint
        decision_type = decision_context.decision_type.lower()
        
        # Core Beast Mode concerns
        perspective.add_concern("Ensure systematic approach over ad-hoc methods")
        perspective.add_concern("Validate PDCA methodology integration")
        perspective.add_concern("Confirm measurable superiority outcomes")
        
        # Decision-type specific analysis
        if 'architecture' in decision_type:
            perspective.add_concern("Architecture must support systematic scalability")
            perspective.add_recommendation("Implement ReflectiveModule pattern for all components")
            perspective.add_recommendation("Ensure comprehensive health monitoring")
            perspective.add_evidence("ReflectiveModule provides systematic operational visibility")
            
        elif 'implementation' in decision_type:
            perspective.add_concern("Implementation must follow systematic patterns")
            perspective.add_recommendation("Use PDCA cycles for implementation phases")
            perspective.add_recommendation("Implement comprehensive testing and validation")
            perspective.add_evidence("PDCA methodology reduces implementation risk")
            
        elif 'process' in decision_type:
            perspective.add_concern("Process must demonstrate measurable improvement")
            perspective.add_recommendation("Implement systematic measurement and feedback loops")
            perspective.add_recommendation("Document process superiority evidence")
            perspective.add_evidence("Systematic processes outperform ad-hoc approaches")
        
        # Universal Beast Mode recommendations
        perspective.add_recommendation("Implement comprehensive metrics collection")
        perspective.add_recommendation("Ensure RCA capabilities for failure analysis")
        perspective.add_recommendation("Document systematic approach benefits")
        
        # Set confidence based on systematic approach alignment
        systematic_indicators = sum(1 for constraint in decision_context.constraints 
                                  if 'systematic' in constraint.lower())
        
        if systematic_indicators >= 2:
            perspective.confidence_level = ConfidenceLevel.HIGH
            perspective.confidence_score = 0.85
            perspective.risk_assessment = RiskLevel.LOW
        elif systematic_indicators >= 1:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.65
            perspective.risk_assessment = RiskLevel.MEDIUM
        else:
            perspective.confidence_level = ConfidenceLevel.LOW
            perspective.confidence_score = 0.35
            perspective.risk_assessment = RiskLevel.HIGH
            perspective.add_concern("Insufficient systematic approach indicators")
        
        return perspective
    
    def gke_consumer_perspective(self, decision_context: DecisionContext) -> StakeholderPerspective:
        """
        Generate GKE consumer perspective focusing on Kubernetes deployment excellence.
        
        Args:
            decision_context: Decision context to analyze
            
        Returns:
            StakeholderPerspective: GKE consumer perspective
        """
        perspective = StakeholderPerspective(
            stakeholder_type=StakeholderType.GKE_CONSUMER,
            viewpoint="GKE Autopilot deployment and operational excellence",
            analyst="GKEConsumerAnalyst"
        )
        
        # GKE-specific concerns and recommendations
        perspective.add_concern("Ensure GKE Autopilot compatibility and optimization")
        perspective.add_concern("Validate serverless Kubernetes best practices")
        perspective.add_concern("Confirm auto-scaling and resource optimization")
        
        decision_type = decision_context.decision_type.lower()
        
        if 'deployment' in decision_type or 'infrastructure' in decision_type:
            perspective.add_recommendation("Use GKE Autopilot for serverless Kubernetes")
            perspective.add_recommendation("Implement comprehensive health checks")
            perspective.add_recommendation("Configure auto-scaling policies")
            perspective.add_evidence("GKE Autopilot reduces operational overhead")
            perspective.add_evidence("Serverless Kubernetes improves resource efficiency")
            
        elif 'architecture' in decision_type:
            perspective.add_recommendation("Design for cloud-native patterns")
            perspective.add_recommendation("Implement 12-factor app principles")
            perspective.add_recommendation("Use Kubernetes-native service discovery")
            perspective.add_evidence("Cloud-native architecture improves scalability")
            
        # Universal GKE recommendations
        perspective.add_recommendation("Implement comprehensive monitoring with Google Cloud Operations")
        perspective.add_recommendation("Use Google Cloud security best practices")
        perspective.add_recommendation("Optimize for cost efficiency")
        
        # Assess confidence based on cloud-native indicators
        cloud_indicators = sum(1 for criterion in decision_context.success_criteria 
                             if any(term in criterion.lower() for term in ['cloud', 'kubernetes', 'scale']))
        
        if cloud_indicators >= 2:
            perspective.confidence_level = ConfidenceLevel.HIGH
            perspective.confidence_score = 0.8
            perspective.risk_assessment = RiskLevel.LOW
        elif cloud_indicators >= 1:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.6
            perspective.risk_assessment = RiskLevel.MEDIUM
        else:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.5
            perspective.risk_assessment = RiskLevel.MEDIUM
        
        return perspective
    
    def developer_perspective(self, decision_context: DecisionContext) -> StakeholderPerspective:
        """
        Generate developer perspective focusing on development experience and maintainability.
        
        Args:
            decision_context: Decision context to analyze
            
        Returns:
            StakeholderPerspective: Developer perspective
        """
        perspective = StakeholderPerspective(
            stakeholder_type=StakeholderType.DEVELOPER,
            viewpoint="Development experience, maintainability, and productivity",
            analyst="DeveloperAdvocate"
        )
        
        # Developer-focused concerns
        perspective.add_concern("Ensure good developer experience and productivity")
        perspective.add_concern("Validate code maintainability and readability")
        perspective.add_concern("Confirm adequate testing and debugging capabilities")
        
        decision_type = decision_context.decision_type.lower()
        
        if 'implementation' in decision_type:
            perspective.add_recommendation("Use clear, self-documenting code patterns")
            perspective.add_recommendation("Implement comprehensive unit and integration tests")
            perspective.add_recommendation("Provide clear error messages and debugging info")
            perspective.add_evidence("Well-tested code reduces debugging time")
            
        elif 'architecture' in decision_type:
            perspective.add_recommendation("Design for modularity and testability")
            perspective.add_recommendation("Use established design patterns")
            perspective.add_recommendation("Minimize coupling between components")
            perspective.add_evidence("Modular architecture improves maintainability")
            
        elif 'process' in decision_type:
            perspective.add_recommendation("Automate repetitive development tasks")
            perspective.add_recommendation("Implement fast feedback loops")
            perspective.add_recommendation("Provide clear development documentation")
            perspective.add_evidence("Automated processes reduce human error")
        
        # Universal developer recommendations
        perspective.add_recommendation("Maintain comprehensive documentation")
        perspective.add_recommendation("Use version control best practices")
        perspective.add_recommendation("Implement code review processes")
        
        # Assess confidence based on development-friendly indicators
        dev_indicators = sum(1 for constraint in decision_context.constraints 
                           if any(term in constraint.lower() for term in ['test', 'document', 'maintain']))
        
        if dev_indicators >= 2:
            perspective.confidence_level = ConfidenceLevel.HIGH
            perspective.confidence_score = 0.75
            perspective.risk_assessment = RiskLevel.LOW
        else:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.6
            perspective.risk_assessment = RiskLevel.MEDIUM
        
        return perspective
    
    def operations_perspective(self, decision_context: DecisionContext) -> StakeholderPerspective:
        """
        Generate operations perspective focusing on reliability, monitoring, and maintenance.
        
        Args:
            decision_context: Decision context to analyze
            
        Returns:
            StakeholderPerspective: Operations perspective
        """
        perspective = StakeholderPerspective(
            stakeholder_type=StakeholderType.OPERATIONS,
            viewpoint="Operational reliability, monitoring, and maintenance excellence",
            analyst="OperationsEngineer"
        )
        
        # Operations-focused concerns
        perspective.add_concern("Ensure high availability and reliability")
        perspective.add_concern("Validate comprehensive monitoring and alerting")
        perspective.add_concern("Confirm maintainability and operational procedures")
        
        decision_type = decision_context.decision_type.lower()
        
        if 'deployment' in decision_type or 'infrastructure' in decision_type:
            perspective.add_recommendation("Implement comprehensive health checks")
            perspective.add_recommendation("Set up monitoring and alerting")
            perspective.add_recommendation("Plan for disaster recovery")
            perspective.add_evidence("Proactive monitoring prevents outages")
            
        elif 'architecture' in decision_type:
            perspective.add_recommendation("Design for fault tolerance")
            perspective.add_recommendation("Implement circuit breakers and retries")
            perspective.add_recommendation("Plan for horizontal scaling")
            perspective.add_evidence("Fault-tolerant design improves reliability")
        
        # Universal operations recommendations
        perspective.add_recommendation("Implement structured logging")
        perspective.add_recommendation("Set up performance monitoring")
        perspective.add_recommendation("Document operational procedures")
        perspective.add_recommendation("Plan for capacity management")
        
        # Assess confidence based on operational indicators
        ops_indicators = sum(1 for criterion in decision_context.success_criteria 
                           if any(term in criterion.lower() for term in ['monitor', 'reliable', 'available']))
        
        if ops_indicators >= 2:
            perspective.confidence_level = ConfidenceLevel.HIGH
            perspective.confidence_score = 0.8
            perspective.risk_assessment = RiskLevel.LOW
        elif ops_indicators >= 1:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.65
            perspective.risk_assessment = RiskLevel.MEDIUM
        else:
            perspective.confidence_level = ConfidenceLevel.LOW
            perspective.confidence_score = 0.4
            perspective.risk_assessment = RiskLevel.HIGH
            perspective.add_concern("Insufficient operational considerations")
        
        return perspective
    
    def security_perspective(self, decision_context: DecisionContext) -> StakeholderPerspective:
        """
        Generate security perspective focusing on security best practices and compliance.
        
        Args:
            decision_context: Decision context to analyze
            
        Returns:
            StakeholderPerspective: Security perspective
        """
        perspective = StakeholderPerspective(
            stakeholder_type=StakeholderType.SECURITY,
            viewpoint="Security best practices, compliance, and risk management",
            analyst="SecurityEngineer"
        )
        
        # Security-focused concerns
        perspective.add_concern("Ensure security best practices implementation")
        perspective.add_concern("Validate data protection and privacy measures")
        perspective.add_concern("Confirm compliance with security standards")
        
        decision_type = decision_context.decision_type.lower()
        
        if 'architecture' in decision_type:
            perspective.add_recommendation("Implement defense in depth")
            perspective.add_recommendation("Use principle of least privilege")
            perspective.add_recommendation("Encrypt data at rest and in transit")
            perspective.add_evidence("Layered security reduces attack surface")
            
        elif 'implementation' in decision_type:
            perspective.add_recommendation("Validate all inputs and sanitize outputs")
            perspective.add_recommendation("Use secure coding practices")
            perspective.add_recommendation("Implement proper authentication and authorization")
            perspective.add_evidence("Input validation prevents injection attacks")
        
        # Universal security recommendations
        perspective.add_recommendation("Conduct regular security assessments")
        perspective.add_recommendation("Implement security monitoring and logging")
        perspective.add_recommendation("Maintain security documentation")
        perspective.add_recommendation("Plan for incident response")
        
        # Assess confidence based on security indicators
        security_indicators = sum(1 for constraint in decision_context.constraints 
                                if any(term in constraint.lower() for term in ['security', 'encrypt', 'auth']))
        
        if security_indicators >= 2:
            perspective.confidence_level = ConfidenceLevel.HIGH
            perspective.confidence_score = 0.85
            perspective.risk_assessment = RiskLevel.LOW
        elif security_indicators >= 1:
            perspective.confidence_level = ConfidenceLevel.MEDIUM
            perspective.confidence_score = 0.65
            perspective.risk_assessment = RiskLevel.MEDIUM
        else:
            perspective.confidence_level = ConfidenceLevel.LOW
            perspective.confidence_score = 0.3
            perspective.risk_assessment = RiskLevel.CRITICAL
            perspective.add_concern("Insufficient security considerations - critical risk")
        
        return perspective
    
    def synthesize_stakeholder_perspectives(self, analysis: MultiStakeholderAnalysis) -> Dict[str, Any]:
        """
        Synthesize multiple stakeholder perspectives into risk-reduced decision recommendations.
        
        Args:
            analysis: Multi-stakeholder analysis to synthesize
            
        Returns:
            Dict[str, Any]: Synthesis results with risk-reduced recommendations
        """
        if not analysis.perspectives:
            return {
                'synthesis_success': False,
                'message': 'No perspectives available for synthesis',
                'recommendations': [],
                'risk_factors': ['No stakeholder input available']
            }
        
        # Calculate consensus and identify conflicts
        analysis.synthesize_perspectives()
        
        # Identify high-risk areas (perspectives with critical or high risk)
        high_risk_perspectives = [
            p for p in analysis.perspectives.values() 
            if p.risk_assessment in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
        
        # Identify low-confidence areas
        low_confidence_perspectives = [
            p for p in analysis.perspectives.values()
            if p.confidence_level in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]
        ]
        
        # Generate risk-reduced recommendations
        risk_reduced_recommendations = []
        
        # Address high-risk concerns first
        for perspective in high_risk_perspectives:
            for concern in perspective.concerns:
                risk_reduced_recommendations.append(f"Address {perspective.stakeholder_type.value} concern: {concern}")
        
        # Include high-confidence recommendations
        high_confidence_recommendations = []
        for perspective in analysis.perspectives.values():
            if perspective.is_high_confidence():
                high_confidence_recommendations.extend(perspective.recommendations)
        
        # Prioritize recommendations by stakeholder consensus
        recommendation_votes = {}
        for perspective in analysis.perspectives.values():
            for rec in perspective.recommendations:
                recommendation_votes[rec] = recommendation_votes.get(rec, 0) + 1
        
        # Sort by consensus (most votes first)
        consensus_recommendations = sorted(
            recommendation_votes.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Build final synthesis
        synthesis_result = {
            'synthesis_success': True,
            'consensus_level': analysis.consensus_level,
            'overall_confidence': analysis.overall_confidence.value,
            'overall_risk': analysis.overall_risk.value,
            'stakeholder_count': len(analysis.perspectives),
            'high_risk_areas': len(high_risk_perspectives),
            'low_confidence_areas': len(low_confidence_perspectives),
            'consensus_recommendations': [rec for rec, votes in consensus_recommendations[:5]],
            'risk_mitigation_actions': risk_reduced_recommendations[:3],
            'identified_conflicts': analysis.identified_conflicts,
            'recommended_outcome': analysis.recommended_outcome.value if analysis.recommended_outcome else None,
            'synthesis_timestamp': datetime.utcnow().isoformat()
        }
        
        return synthesis_result
    
    def get_analysis(self, analysis_id: str) -> Optional[MultiStakeholderAnalysis]:
        """Get an analysis by ID."""
        if analysis_id in self._active_analyses:
            return self._active_analyses[analysis_id]
        elif analysis_id in self._completed_analyses:
            return self._completed_analyses[analysis_id]
        return None
    
    def complete_analysis(self, analysis_id: str) -> bool:
        """Complete an active analysis and move it to completed."""
        if analysis_id not in self._active_analyses:
            return False
        
        analysis = self._active_analyses[analysis_id]
        analysis.complete_analysis()
        
        # Move to completed
        self._completed_analyses[analysis_id] = analysis
        del self._active_analyses[analysis_id]
        
        return True
    
    def _generate_stakeholder_perspective(self, stakeholder_type: StakeholderType,
                                        decision_context: DecisionContext) -> StakeholderPerspective:
        """Generate a perspective for a specific stakeholder type."""
        # Route to appropriate perspective method
        if stakeholder_type == StakeholderType.BEAST_MODE:
            return self.beast_mode_perspective(decision_context)
        elif stakeholder_type == StakeholderType.GKE_CONSUMER:
            return self.gke_consumer_perspective(decision_context)
        elif stakeholder_type == StakeholderType.DEVELOPER:
            return self.developer_perspective(decision_context)
        elif stakeholder_type == StakeholderType.OPERATIONS:
            return self.operations_perspective(decision_context)
        elif stakeholder_type == StakeholderType.SECURITY:
            return self.security_perspective(decision_context)
        else:
            # Generic perspective for other stakeholder types
            return self._generate_generic_perspective(stakeholder_type, decision_context)
    
    def _generate_generic_perspective(self, stakeholder_type: StakeholderType,
                                    decision_context: DecisionContext) -> StakeholderPerspective:
        """Generate a generic perspective for stakeholder types without specific methods."""
        perspective = StakeholderPerspective(
            stakeholder_type=stakeholder_type,
            viewpoint=f"Generic {stakeholder_type.value} perspective",
            analyst="GenericAnalyst"
        )
        
        # Add generic concerns and recommendations
        perspective.add_concern(f"Ensure {stakeholder_type.value} requirements are met")
        perspective.add_recommendation(f"Consider {stakeholder_type.value} specific needs")
        perspective.add_evidence(f"Stakeholder input improves decision quality")
        
        # Set moderate confidence
        perspective.confidence_level = ConfidenceLevel.MEDIUM
        perspective.confidence_score = 0.5
        perspective.risk_assessment = RiskLevel.MEDIUM
        
        return perspective
    
    def _determine_required_stakeholders(self, decision_context: DecisionContext) -> Set[StakeholderType]:
        """Determine required stakeholders based on decision context."""
        required = set()
        
        # Always include Beast Mode perspective for systematic analysis
        required.add(StakeholderType.BEAST_MODE)
        
        decision_type = decision_context.decision_type.lower()
        
        # Add stakeholders based on decision type
        if 'architecture' in decision_type:
            required.update([StakeholderType.DEVELOPER, StakeholderType.OPERATIONS, StakeholderType.SECURITY])
        
        if 'deployment' in decision_type or 'infrastructure' in decision_type:
            required.update([StakeholderType.GKE_CONSUMER, StakeholderType.OPERATIONS])
        
        if 'implementation' in decision_type:
            required.update([StakeholderType.DEVELOPER, StakeholderType.SECURITY])
        
        if 'process' in decision_type:
            required.update([StakeholderType.DEVELOPER, StakeholderType.OPERATIONS])
        
        # Add stakeholders based on context keywords
        context_text = f"{decision_context.description} {' '.join(decision_context.constraints)}".lower()
        
        if any(term in context_text for term in ['security', 'auth', 'encrypt']):
            required.add(StakeholderType.SECURITY)
        
        if any(term in context_text for term in ['kubernetes', 'gke', 'cloud']):
            required.add(StakeholderType.GKE_CONSUMER)
        
        if any(term in context_text for term in ['user', 'interface', 'experience']):
            required.add(StakeholderType.END_USER)
        
        return required
    
    def _update_performance_metrics(self, analysis: MultiStakeholderAnalysis) -> None:
        """Update performance metrics based on completed analysis."""
        self._performance_metrics['total_analyses'] += 1
        
        if analysis.is_complete() and analysis.has_required_stakeholders():
            self._performance_metrics['successful_analyses'] += 1
        
        # Update average analysis time
        if analysis.analysis_duration:
            total = self._performance_metrics['total_analyses']
            current_avg = self._performance_metrics['average_analysis_time']
            new_time = analysis.analysis_duration.total_seconds()
            
            self._performance_metrics['average_analysis_time'] = (
                (current_avg * (total - 1) + new_time) / total
            )
        
        # Update consensus achievement rate
        if analysis.consensus_level >= 0.6:  # Consider 60%+ as consensus achieved
            total = self._performance_metrics['total_analyses']
            current_consensus = self._performance_metrics['consensus_achievement_rate'] * (total - 1)
            self._performance_metrics['consensus_achievement_rate'] = (current_consensus + 1) / total
    
    def _initialize_stakeholder_capabilities(self) -> Dict[StakeholderType, Dict[str, Any]]:
        """Initialize stakeholder capabilities mapping."""
        return {
            StakeholderType.BEAST_MODE: {
                'systematic_analysis': 'Expert',
                'pdca_methodology': 'Expert',
                'superiority_measurement': 'Expert',
                'pattern_recognition': 'Advanced'
            },
            StakeholderType.GKE_CONSUMER: {
                'kubernetes_expertise': 'Expert',
                'cloud_native_patterns': 'Expert',
                'scalability_analysis': 'Advanced',
                'cost_optimization': 'Advanced'
            },
            StakeholderType.DEVELOPER: {
                'code_quality': 'Expert',
                'maintainability': 'Expert',
                'testing_strategies': 'Advanced',
                'development_experience': 'Expert'
            },
            StakeholderType.OPERATIONS: {
                'reliability_engineering': 'Expert',
                'monitoring_alerting': 'Expert',
                'incident_response': 'Advanced',
                'capacity_planning': 'Advanced'
            },
            StakeholderType.SECURITY: {
                'security_architecture': 'Expert',
                'threat_modeling': 'Expert',
                'compliance_assessment': 'Advanced',
                'risk_analysis': 'Expert'
            }
        }