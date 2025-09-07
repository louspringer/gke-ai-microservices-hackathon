"""
Core data models for Beast Mode Framework.

This module provides the foundational data structures for systematic
multi-stakeholder analysis, model-driven decision making, and PDCA
methodology implementation.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator
import uuid


class StakeholderType(str, Enum):
    """Types of stakeholders in multi-perspective analysis."""
    BEAST_MODE = "beast_mode"
    GKE_CONSUMER = "gke_consumer"
    TIDB_CONSUMER = "tidb_consumer"
    DEVELOPER = "developer"
    OPERATIONS = "operations"
    SECURITY = "security"
    BUSINESS = "business"
    END_USER = "end_user"
    SYSTEM = "system"


class ConfidenceLevel(str, Enum):
    """Confidence levels for decisions and analysis."""
    VERY_LOW = "very_low"      # < 25%
    LOW = "low"                # 25-49%
    MEDIUM = "medium"          # 50-74%
    HIGH = "high"              # 75-89%
    VERY_HIGH = "very_high"    # 90-100%


class DecisionOutcome(str, Enum):
    """Possible outcomes of a decision process."""
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    REQUIRES_MORE_INFO = "requires_more_info"
    ESCALATED = "escalated"
    CONSENSUS_REACHED = "consensus_reached"
    NO_CONSENSUS = "no_consensus"


class RiskLevel(str, Enum):
    """Risk levels for decisions and implementations."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StakeholderPerspective:
    """
    Represents a single stakeholder's perspective on a decision or analysis.
    
    This class captures the viewpoint, concerns, and recommendations of a
    specific stakeholder type in the multi-perspective analysis process.
    """
    
    stakeholder_type: StakeholderType
    perspective_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Core perspective data
    viewpoint: str = ""
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Confidence and risk assessment
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.5  # 0.0 to 1.0
    risk_assessment: RiskLevel = RiskLevel.MEDIUM
    
    # Supporting data
    supporting_evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    analyst: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure confidence score matches confidence level
        if self.confidence_level == ConfidenceLevel.VERY_LOW:
            self.confidence_score = min(self.confidence_score, 0.24)
        elif self.confidence_level == ConfidenceLevel.LOW:
            self.confidence_score = max(0.25, min(self.confidence_score, 0.49))
        elif self.confidence_level == ConfidenceLevel.MEDIUM:
            self.confidence_score = max(0.50, min(self.confidence_score, 0.74))
        elif self.confidence_level == ConfidenceLevel.HIGH:
            self.confidence_score = max(0.75, min(self.confidence_score, 0.89))
        elif self.confidence_level == ConfidenceLevel.VERY_HIGH:
            self.confidence_score = max(0.90, self.confidence_score)
    
    def add_concern(self, concern: str) -> None:
        """Add a concern to this perspective."""
        if concern and concern not in self.concerns:
            self.concerns.append(concern)
    
    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation to this perspective."""
        if recommendation and recommendation not in self.recommendations:
            self.recommendations.append(recommendation)
    
    def add_evidence(self, evidence: str) -> None:
        """Add supporting evidence to this perspective."""
        if evidence and evidence not in self.supporting_evidence:
            self.supporting_evidence.append(evidence)
    
    def is_high_confidence(self) -> bool:
        """Check if this perspective has high confidence."""
        return self.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]
    
    def is_high_risk(self) -> bool:
        """Check if this perspective identifies high risk."""
        return self.risk_assessment in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of this perspective."""
        return {
            'stakeholder_type': self.stakeholder_type.value,
            'confidence_level': self.confidence_level.value,
            'confidence_score': self.confidence_score,
            'risk_level': self.risk_assessment.value,
            'num_concerns': len(self.concerns),
            'num_recommendations': len(self.recommendations),
            'viewpoint_preview': self.viewpoint[:100] + "..." if len(self.viewpoint) > 100 else self.viewpoint,
        }


class DecisionContext(BaseModel):
    """
    Context information for a decision that requires multi-stakeholder analysis.
    """
    
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    
    # Decision metadata
    decision_type: str = Field(..., min_length=1)  # e.g., "architecture", "implementation", "process"
    priority: str = Field(default="medium")  # low, medium, high, critical
    urgency: str = Field(default="normal")   # low, normal, high, urgent
    
    # Context data
    background: str = ""
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    
    # Stakeholder requirements
    required_stakeholders: Set[StakeholderType] = Field(default_factory=set)
    optional_stakeholders: Set[StakeholderType] = Field(default_factory=set)
    
    # Timing and deadlines
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    estimated_analysis_time: Optional[timedelta] = None
    
    # Additional context
    related_decisions: List[str] = Field(default_factory=list)
    tags: Set[str] = Field(default_factory=set)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds(),
            set: lambda v: list(v),
        }
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Validate priority level."""
        allowed = {'low', 'medium', 'high', 'critical'}
        if v not in allowed:
            raise ValueError(f'Priority must be one of: {allowed}')
        return v
    
    @field_validator('urgency')
    @classmethod
    def validate_urgency(cls, v):
        """Validate urgency level."""
        allowed = {'low', 'normal', 'high', 'urgent'}
        if v not in allowed:
            raise ValueError(f'Urgency must be one of: {allowed}')
        return v
    
    def is_high_priority(self) -> bool:
        """Check if this is a high priority decision."""
        return self.priority in ['high', 'critical']
    
    def is_urgent(self) -> bool:
        """Check if this decision is urgent."""
        return self.urgency in ['high', 'urgent']
    
    def is_overdue(self) -> bool:
        """Check if the decision deadline has passed."""
        return self.deadline is not None and datetime.utcnow() > self.deadline
    
    def time_remaining(self) -> Optional[timedelta]:
        """Get time remaining until deadline."""
        if self.deadline is None:
            return None
        remaining = self.deadline - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def add_constraint(self, constraint: str) -> None:
        """Add a constraint to the decision context."""
        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)
    
    def add_success_criterion(self, criterion: str) -> None:
        """Add a success criterion."""
        if criterion and criterion not in self.success_criteria:
            self.success_criteria.append(criterion)
    
    def require_stakeholder(self, stakeholder: StakeholderType) -> None:
        """Mark a stakeholder as required for this decision."""
        self.required_stakeholders.add(stakeholder)
        self.optional_stakeholders.discard(stakeholder)
    
    def add_optional_stakeholder(self, stakeholder: StakeholderType) -> None:
        """Add an optional stakeholder for this decision."""
        if stakeholder not in self.required_stakeholders:
            self.optional_stakeholders.add(stakeholder)


class MultiStakeholderAnalysis(BaseModel):
    """
    Comprehensive multi-stakeholder analysis for systematic decision making.
    
    This class orchestrates the collection and synthesis of perspectives from
    multiple stakeholders to reduce decision risk and improve outcomes through
    systematic analysis rather than ad-hoc approaches.
    """
    
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_context: DecisionContext
    
    # Stakeholder perspectives
    perspectives: Dict[str, StakeholderPerspective] = Field(default_factory=dict)
    
    # Analysis results
    consensus_level: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    overall_risk: RiskLevel = RiskLevel.MEDIUM
    
    # Synthesis results
    synthesized_recommendations: List[str] = Field(default_factory=list)
    identified_conflicts: List[str] = Field(default_factory=list)
    risk_mitigation_strategies: List[str] = Field(default_factory=list)
    
    # Decision outcome
    recommended_outcome: Optional[DecisionOutcome] = None
    outcome_rationale: str = ""
    
    # Process metadata
    analysis_started: datetime = Field(default_factory=datetime.utcnow)
    analysis_completed: Optional[datetime] = None
    analysis_duration: Optional[timedelta] = None
    
    # Quality metrics
    stakeholder_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    perspective_diversity: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds(),
        }
    
    def add_perspective(self, perspective: StakeholderPerspective) -> None:
        """Add a stakeholder perspective to the analysis."""
        key = f"{perspective.stakeholder_type.value}_{perspective.perspective_id}"
        self.perspectives[key] = perspective
        self._update_metrics()
    
    def get_perspective(self, stakeholder_type: StakeholderType) -> Optional[StakeholderPerspective]:
        """Get the first perspective for a stakeholder type."""
        for perspective in self.perspectives.values():
            if perspective.stakeholder_type == stakeholder_type:
                return perspective
        return None
    
    def get_all_perspectives(self, stakeholder_type: StakeholderType) -> List[StakeholderPerspective]:
        """Get all perspectives for a stakeholder type."""
        return [p for p in self.perspectives.values() if p.stakeholder_type == stakeholder_type]
    
    def calculate_consensus(self) -> float:
        """
        Calculate consensus level across all perspectives.
        
        Returns:
            float: Consensus level from 0.0 (no consensus) to 1.0 (full consensus)
        """
        if not self.perspectives:
            return 0.0
        
        # Simple consensus calculation based on confidence alignment
        confidence_scores = [p.confidence_score for p in self.perspectives.values()]
        
        if not confidence_scores:
            return 0.0
        
        # Calculate variance in confidence scores
        mean_confidence = sum(confidence_scores) / len(confidence_scores)
        variance = sum((score - mean_confidence) ** 2 for score in confidence_scores) / len(confidence_scores)
        
        # Convert variance to consensus (lower variance = higher consensus)
        max_variance = 0.25  # Maximum expected variance
        consensus = max(0.0, 1.0 - (variance / max_variance))
        
        self.consensus_level = min(1.0, consensus)
        return self.consensus_level
    
    def synthesize_perspectives(self) -> None:
        """
        Synthesize all perspectives into unified recommendations and risk assessment.
        """
        if not self.perspectives:
            return
        
        # Collect all recommendations
        all_recommendations = []
        all_concerns = []
        
        for perspective in self.perspectives.values():
            all_recommendations.extend(perspective.recommendations)
            all_concerns.extend(perspective.concerns)
        
        # Find common recommendations (mentioned by multiple stakeholders)
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Prioritize recommendations mentioned by multiple stakeholders
        self.synthesized_recommendations = [
            rec for rec, count in sorted(recommendation_counts.items(), key=lambda x: x[1], reverse=True)
            if count > 1 or len(self.perspectives) == 1
        ]
        
        # Identify conflicts (concerns that contradict recommendations)
        self.identified_conflicts = []
        for concern in set(all_concerns):
            for rec in self.synthesized_recommendations:
                if self._are_conflicting(concern, rec):
                    conflict = f"Concern: '{concern}' conflicts with recommendation: '{rec}'"
                    if conflict not in self.identified_conflicts:
                        self.identified_conflicts.append(conflict)
        
        # Calculate overall metrics
        self._calculate_overall_confidence()
        self._calculate_overall_risk()
        self.calculate_consensus()
        
        # Determine recommended outcome
        self._determine_recommended_outcome()
    
    def complete_analysis(self) -> None:
        """Mark the analysis as completed and calculate final metrics."""
        self.analysis_completed = datetime.utcnow()
        self.analysis_duration = self.analysis_completed - self.analysis_started
        self.synthesize_perspectives()
        self._update_metrics()
    
    def is_complete(self) -> bool:
        """Check if the analysis is complete."""
        return self.analysis_completed is not None
    
    def has_required_stakeholders(self) -> bool:
        """Check if all required stakeholders have provided perspectives."""
        provided_types = {p.stakeholder_type for p in self.perspectives.values()}
        return self.decision_context.required_stakeholders.issubset(provided_types)
    
    def get_missing_stakeholders(self) -> Set[StakeholderType]:
        """Get the set of required stakeholders that haven't provided perspectives."""
        provided_types = {p.stakeholder_type for p in self.perspectives.values()}
        return self.decision_context.required_stakeholders - provided_types
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the analysis."""
        return {
            'analysis_id': self.analysis_id,
            'decision_title': self.decision_context.title,
            'stakeholder_count': len(self.perspectives),
            'consensus_level': self.consensus_level,
            'overall_confidence': self.overall_confidence,
            'overall_risk': self.overall_risk,
            'recommended_outcome': self.recommended_outcome if self.recommended_outcome else None,
            'num_recommendations': len(self.synthesized_recommendations),
            'num_conflicts': len(self.identified_conflicts),
            'is_complete': self.is_complete(),
            'has_required_stakeholders': self.has_required_stakeholders(),
            'analysis_duration_seconds': self.analysis_duration.total_seconds() if self.analysis_duration else None,
        }
    
    def _update_metrics(self) -> None:
        """Update quality metrics based on current perspectives."""
        if not self.perspectives:
            self.stakeholder_coverage = 0.0
            self.perspective_diversity = 0.0
            self.evidence_quality = 0.0
            return
        
        # Calculate stakeholder coverage
        required_count = len(self.decision_context.required_stakeholders)
        provided_types = {p.stakeholder_type for p in self.perspectives.values()}
        provided_required = len(provided_types.intersection(self.decision_context.required_stakeholders))
        
        if required_count > 0:
            self.stakeholder_coverage = provided_required / required_count
        else:
            self.stakeholder_coverage = 1.0
        
        # Calculate perspective diversity (variety of stakeholder types)
        total_possible_types = len(StakeholderType)
        unique_types = len(provided_types)
        self.perspective_diversity = unique_types / total_possible_types
        
        # Calculate evidence quality (average evidence count per perspective)
        evidence_counts = [len(p.supporting_evidence) for p in self.perspectives.values()]
        avg_evidence = sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0
        max_expected_evidence = 5  # Assume 5 pieces of evidence is high quality
        self.evidence_quality = min(1.0, avg_evidence / max_expected_evidence)
    
    def _calculate_overall_confidence(self) -> None:
        """Calculate overall confidence level from all perspectives."""
        if not self.perspectives:
            self.overall_confidence = ConfidenceLevel.MEDIUM
            return
        
        confidence_scores = [p.confidence_score for p in self.perspectives.values()]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        if avg_confidence < 0.25:
            self.overall_confidence = ConfidenceLevel.VERY_LOW
        elif avg_confidence < 0.50:
            self.overall_confidence = ConfidenceLevel.LOW
        elif avg_confidence < 0.75:
            self.overall_confidence = ConfidenceLevel.MEDIUM
        elif avg_confidence < 0.90:
            self.overall_confidence = ConfidenceLevel.HIGH
        else:
            self.overall_confidence = ConfidenceLevel.VERY_HIGH
    
    def _calculate_overall_risk(self) -> None:
        """Calculate overall risk level from all perspectives."""
        if not self.perspectives:
            self.overall_risk = RiskLevel.MEDIUM
            return
        
        # Take the highest risk level identified by any stakeholder
        risk_levels = [p.risk_assessment for p in self.perspectives.values()]
        risk_values = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.CRITICAL: 5
        }
        
        max_risk_value = max(risk_values[risk] for risk in risk_levels)
        
        for risk_level, value in risk_values.items():
            if value == max_risk_value:
                self.overall_risk = risk_level
                break
    
    def _determine_recommended_outcome(self) -> None:
        """Determine the recommended outcome based on analysis results."""
        if not self.perspectives:
            self.recommended_outcome = DecisionOutcome.REQUIRES_MORE_INFO
            self.outcome_rationale = "No stakeholder perspectives available"
            return
        
        # Check if we have required stakeholders
        if not self.has_required_stakeholders():
            self.recommended_outcome = DecisionOutcome.REQUIRES_MORE_INFO
            missing = [s.value for s in self.get_missing_stakeholders()]
            self.outcome_rationale = f"Missing required stakeholders: {', '.join(missing)}"
            return
        
        # Check consensus level
        if self.consensus_level < 0.3:
            self.recommended_outcome = DecisionOutcome.NO_CONSENSUS
            self.outcome_rationale = f"Low consensus level: {self.consensus_level:.2f}"
            return
        
        # Check overall risk
        if self.overall_risk == RiskLevel.CRITICAL:
            self.recommended_outcome = DecisionOutcome.ESCALATED
            self.outcome_rationale = "Critical risk level requires escalation"
            return
        
        # Check confidence level
        if self.overall_confidence in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
            self.recommended_outcome = DecisionOutcome.REQUIRES_MORE_INFO
            self.outcome_rationale = f"Low confidence level: {self.overall_confidence}"
            return
        
        # Check for significant conflicts
        if len(self.identified_conflicts) > len(self.synthesized_recommendations):
            self.recommended_outcome = DecisionOutcome.DEFERRED
            self.outcome_rationale = "Too many conflicts identified relative to recommendations"
            return
        
        # If we get here, conditions are favorable
        if self.consensus_level >= 0.7 and self.overall_confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]:
            self.recommended_outcome = DecisionOutcome.CONSENSUS_REACHED
            self.outcome_rationale = f"High consensus ({self.consensus_level:.2f}) and confidence ({self.overall_confidence})"
        else:
            self.recommended_outcome = DecisionOutcome.APPROVED
            self.outcome_rationale = f"Adequate consensus ({self.consensus_level:.2f}) and confidence ({self.overall_confidence})"
    
    def _are_conflicting(self, concern: str, recommendation: str) -> bool:
        """
        Simple heuristic to detect if a concern conflicts with a recommendation.
        
        In a real implementation, this would use NLP or more sophisticated analysis.
        """
        # Simple keyword-based conflict detection
        negative_words = ['not', 'avoid', 'prevent', 'stop', 'block', 'reject', 'refuse']
        concern_lower = concern.lower()
        rec_lower = recommendation.lower()
        
        # Check if concern contains negative words and shares keywords with recommendation
        concern_has_negative = any(word in concern_lower for word in negative_words)
        
        if concern_has_negative:
            # Look for shared keywords (simple approach)
            concern_words = set(concern_lower.split())
            rec_words = set(rec_lower.split())
            shared_words = concern_words.intersection(rec_words)
            
            # If they share significant words and concern is negative, likely conflicting
            return len(shared_words) >= 2
        
        return False


class ModelDrivenDecisionResult(BaseModel):
    """
    Result of a model-driven decision process using systematic analysis.
    
    This class captures the complete decision process, from initial context
    through multi-stakeholder analysis to final outcome and implementation plan.
    """
    
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_context: DecisionContext
    analysis: MultiStakeholderAnalysis
    
    # Final decision
    final_decision: DecisionOutcome
    decision_rationale: str
    decision_maker: str = ""
    decision_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Implementation details
    implementation_plan: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    monitoring_plan: List[str] = Field(default_factory=list)
    
    # Risk management
    identified_risks: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)
    contingency_plans: List[str] = Field(default_factory=list)
    
    # Quality and traceability
    decision_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    systematic_approach_used: bool = True
    pdca_cycle_planned: bool = False
    
    # Follow-up and review
    review_scheduled: Optional[datetime] = None
    review_criteria: List[str] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def calculate_quality_score(self) -> float:
        """
        Calculate the quality score of the decision process.
        
        Returns:
            float: Quality score from 0.0 to 1.0
        """
        score_components = []
        
        # Analysis completeness (30%)
        if self.analysis.is_complete():
            score_components.append(0.3)
        else:
            score_components.append(0.0)
        
        # Stakeholder coverage (25%)
        coverage_score = self.analysis.stakeholder_coverage * 0.25
        score_components.append(coverage_score)
        
        # Consensus level (20%)
        consensus_score = self.analysis.consensus_level * 0.20
        score_components.append(consensus_score)
        
        # Evidence quality (15%)
        evidence_score = self.analysis.evidence_quality * 0.15
        score_components.append(evidence_score)
        
        # Implementation planning (10%)
        impl_score = min(1.0, len(self.implementation_plan) / 5) * 0.10
        score_components.append(impl_score)
        
        self.decision_quality_score = sum(score_components)
        return self.decision_quality_score
    
    def add_implementation_step(self, step: str) -> None:
        """Add an implementation step."""
        if step and step not in self.implementation_plan:
            self.implementation_plan.append(step)
    
    def add_success_metric(self, metric: str) -> None:
        """Add a success metric."""
        if metric and metric not in self.success_metrics:
            self.success_metrics.append(metric)
    
    def add_risk(self, risk: str, mitigation: Optional[str] = None) -> None:
        """Add an identified risk and optional mitigation strategy."""
        if risk and risk not in self.identified_risks:
            self.identified_risks.append(risk)
        
        if mitigation and mitigation not in self.mitigation_strategies:
            self.mitigation_strategies.append(mitigation)
    
    def schedule_review(self, review_date: datetime, criteria: List[str]) -> None:
        """Schedule a decision review."""
        self.review_scheduled = review_date
        self.review_criteria.extend([c for c in criteria if c not in self.review_criteria])
    
    def add_lesson_learned(self, lesson: str) -> None:
        """Add a lesson learned from the decision process."""
        if lesson and lesson not in self.lessons_learned:
            self.lessons_learned.append(lesson)
    
    def is_high_quality_decision(self) -> bool:
        """Check if this represents a high-quality decision process."""
        self.calculate_quality_score()
        return (self.decision_quality_score >= 0.8 and 
                self.systematic_approach_used and
                self.analysis.is_complete())
    
    def get_decision_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the decision result."""
        return {
            'result_id': self.result_id,
            'decision_title': self.decision_context.title,
            'final_decision': self.final_decision,
            'decision_quality_score': self.calculate_quality_score(),
            'systematic_approach': self.systematic_approach_used,
            'stakeholder_count': len(self.analysis.perspectives),
            'consensus_level': self.analysis.consensus_level,
            'overall_confidence': self.analysis.overall_confidence,
            'overall_risk': self.analysis.overall_risk,
            'implementation_steps': len(self.implementation_plan),
            'identified_risks': len(self.identified_risks),
            'is_high_quality': self.is_high_quality_decision(),
            'decision_timestamp': self.decision_timestamp.isoformat(),
        }