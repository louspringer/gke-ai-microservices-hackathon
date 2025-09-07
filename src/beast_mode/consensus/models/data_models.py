"""Data models for multi-agent consensus engine."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator
import uuid


class ConsensusMethod(str, Enum):
    """Methods for calculating consensus."""
    SIMPLE_VOTING = "simple_voting"
    WEIGHTED_CONSENSUS = "weighted_consensus"
    BAYESIAN_CONSENSUS = "bayesian_consensus"
    THRESHOLD_CONSENSUS = "threshold_consensus"


class ConflictType(str, Enum):
    """Types of conflicts between agent analyses."""
    VALUE_DISAGREEMENT = "value_disagreement"
    CONFIDENCE_MISMATCH = "confidence_mismatch"
    METHODOLOGY_CONFLICT = "methodology_conflict"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    SCOPE_DISAGREEMENT = "scope_disagreement"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    AUTOMATIC_VOTING = "automatic_voting"
    WEIGHTED_RESOLUTION = "weighted_resolution"
    EXPERT_RULES = "expert_rules"
    HUMAN_ESCALATION = "human_escalation"
    DEFER_DECISION = "defer_decision"


@dataclass
class AgentAnalysis:
    """
    Analysis result from a single agent.
    
    This class represents the output from an individual agent that will
    be used in the consensus calculation process.
    """
    
    agent_id: str
    analysis_type: str
    result: Any
    confidence: float = field(default=0.5)
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Quality metrics
    completeness_score: float = field(default=1.0)
    consistency_score: float = field(default=1.0)
    reliability_score: float = field(default=1.0)
    
    def __post_init__(self):
        """Validate analysis data after initialization."""
        # Ensure confidence is between 0 and 1
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        # Ensure quality scores are between 0 and 1
        self.completeness_score = max(0.0, min(1.0, self.completeness_score))
        self.consistency_score = max(0.0, min(1.0, self.consistency_score))
        self.reliability_score = max(0.0, min(1.0, self.reliability_score))
    
    def get_overall_quality(self) -> float:
        """Calculate overall quality score."""
        return (self.completeness_score + self.consistency_score + self.reliability_score) / 3.0
    
    def get_weighted_confidence(self) -> float:
        """Get confidence weighted by quality."""
        return self.confidence * self.get_overall_quality()
    
    def add_evidence(self, evidence: str) -> None:
        """Add evidence to support this analysis."""
        if evidence and evidence not in self.evidence:
            self.evidence.append(evidence)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for this analysis."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this analysis has high confidence."""
        return self.get_weighted_confidence() >= threshold
    
    def is_recent(self, max_age_seconds: int = 3600) -> bool:
        """Check if this analysis is recent."""
        age = datetime.utcnow() - self.timestamp
        return age.total_seconds() <= max_age_seconds


class ConsensusResult(BaseModel):
    """
    Result of a consensus calculation.
    
    This class contains the outcome of applying consensus algorithms
    to multiple agent analyses.
    """
    
    consensus_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consensus_value: Any
    confidence_score: float = Field(ge=0.0, le=1.0)
    consensus_method: ConsensusMethod
    
    # Participation metrics
    participating_agents: List[str] = Field(default_factory=list)
    total_agents: int = 0
    agreement_level: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Conflict information
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    unresolved_conflicts: List[str] = Field(default_factory=list)
    
    # Process metadata
    calculation_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    audit_trail: List[str] = Field(default_factory=list)
    
    # Quality metrics
    result_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty_level: float = Field(default=0.0, ge=0.0, le=1.0)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def add_audit_entry(self, entry: str) -> None:
        """Add an entry to the audit trail."""
        timestamp = datetime.utcnow().isoformat()
        self.audit_trail.append(f"[{timestamp}] {entry}")
    
    def is_high_quality(self, quality_threshold: float = 0.8) -> bool:
        """Check if this consensus result is high quality."""
        return (self.result_quality >= quality_threshold and 
                self.confidence_score >= quality_threshold and
                self.agreement_level >= quality_threshold)
    
    def is_reliable(self, min_agents: int = 2, min_agreement: float = 0.6) -> bool:
        """Check if this consensus result is reliable."""
        return (len(self.participating_agents) >= min_agents and
                self.agreement_level >= min_agreement and
                self.conflicts_resolved >= self.conflicts_detected * 0.8)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the consensus result."""
        return {
            'consensus_id': self.consensus_id,
            'method': self.consensus_method,
            'confidence': self.confidence_score,
            'agreement_level': self.agreement_level,
            'participating_agents': len(self.participating_agents),
            'conflicts_resolved': f"{self.conflicts_resolved}/{self.conflicts_detected}",
            'quality': self.result_quality,
            'uncertainty': self.uncertainty_level,
            'calculation_time_ms': self.calculation_time_ms,
            'is_reliable': self.is_reliable(),
        }


class DecisionWorkflow(BaseModel):
    """
    Workflow configuration for multi-agent decision processes.
    
    This class defines how a complex decision should be orchestrated
    across multiple agents with specific requirements and constraints.
    """
    
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: str = Field(..., min_length=1)
    description: str = ""
    
    # Agent requirements
    required_agents: List[str] = Field(default_factory=list)
    optional_agents: List[str] = Field(default_factory=list)
    minimum_agents: int = Field(default=1, ge=1)
    
    # Consensus requirements
    consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED_CONSENSUS
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Timing constraints
    timeout_seconds: int = Field(default=300, ge=1)
    agent_timeout_seconds: int = Field(default=60, ge=1)
    
    # Escalation rules
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)
    auto_escalate_on_conflict: bool = False
    max_resolution_attempts: int = Field(default=3, ge=1)
    
    # Workflow state
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, escalated
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @field_validator('consensus_threshold', 'confidence_threshold')
    @classmethod
    def validate_thresholds(cls, v):
        """Validate threshold values."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Thresholds must be between 0.0 and 1.0')
        return v
    
    def start_workflow(self) -> None:
        """Mark the workflow as started."""
        self.started_at = datetime.utcnow()
        self.status = "running"
    
    def complete_workflow(self) -> None:
        """Mark the workflow as completed."""
        self.completed_at = datetime.utcnow()
        self.status = "completed"
    
    def fail_workflow(self) -> None:
        """Mark the workflow as failed."""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
    
    def escalate_workflow(self) -> None:
        """Mark the workflow as escalated."""
        self.completed_at = datetime.utcnow()
        self.status = "escalated"
    
    def is_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self.status == "running"
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete."""
        return self.status in ["completed", "failed", "escalated"]
    
    def is_timed_out(self) -> bool:
        """Check if the workflow has timed out."""
        if not self.started_at:
            return False
        
        elapsed = datetime.utcnow() - self.started_at
        return elapsed.total_seconds() > self.timeout_seconds
    
    def get_remaining_time(self) -> Optional[timedelta]:
        """Get remaining time before timeout."""
        if not self.started_at:
            return timedelta(seconds=self.timeout_seconds)
        
        elapsed = datetime.utcnow() - self.started_at
        remaining_seconds = self.timeout_seconds - elapsed.total_seconds()
        
        if remaining_seconds <= 0:
            return timedelta(0)
        
        return timedelta(seconds=remaining_seconds)
    
    def add_required_agent(self, agent_id: str) -> None:
        """Add a required agent to the workflow."""
        if agent_id not in self.required_agents:
            self.required_agents.append(agent_id)
        # Remove from optional if present
        if agent_id in self.optional_agents:
            self.optional_agents.remove(agent_id)
    
    def add_optional_agent(self, agent_id: str) -> None:
        """Add an optional agent to the workflow."""
        if agent_id not in self.required_agents and agent_id not in self.optional_agents:
            self.optional_agents.append(agent_id)


@dataclass
class ConflictInfo:
    """
    Information about a conflict between agent analyses.
    
    This class describes conflicts detected during consensus calculation
    and provides context for resolution strategies.
    """
    
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.VALUE_DISAGREEMENT
    severity: float = field(default=0.5)  # 0.0 to 1.0
    
    # Conflicting analyses
    conflicting_agents: List[str] = field(default_factory=list)
    conflict_description: str = ""
    
    # Resolution information
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolution_confidence: float = field(default=0.0)
    resolution_rationale: str = ""
    
    # Metadata
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_attempts: int = 0
    
    def __post_init__(self):
        """Validate conflict data after initialization."""
        self.severity = max(0.0, min(1.0, self.severity))
        self.resolution_confidence = max(0.0, min(1.0, self.resolution_confidence))
    
    def is_severe(self, threshold: float = 0.7) -> bool:
        """Check if this is a severe conflict."""
        return self.severity >= threshold
    
    def is_resolved(self) -> bool:
        """Check if this conflict has been resolved."""
        return self.resolved_at is not None
    
    def attempt_resolution(self, strategy: ResolutionStrategy, rationale: str = "") -> None:
        """Record a resolution attempt."""
        self.resolution_attempts += 1
        self.resolution_strategy = strategy
        self.resolution_rationale = rationale
    
    def resolve_conflict(self, confidence: float = 1.0) -> None:
        """Mark the conflict as resolved."""
        self.resolved_at = datetime.utcnow()
        self.resolution_confidence = max(0.0, min(1.0, confidence))
    
    def get_age(self) -> timedelta:
        """Get the age of this conflict."""
        return datetime.utcnow() - self.detected_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'conflict_id': self.conflict_id,
            'type': self.conflict_type.value,
            'severity': self.severity,
            'agents': self.conflicting_agents,
            'description': self.conflict_description,
            'strategy': self.resolution_strategy.value if self.resolution_strategy else None,
            'confidence': self.resolution_confidence,
            'resolved': self.is_resolved(),
            'attempts': self.resolution_attempts,
            'age_seconds': self.get_age().total_seconds(),
        }


@dataclass
class ResolutionResult:
    """
    Result of a conflict resolution attempt.
    
    This class contains the outcome of applying resolution strategies
    to conflicts between agent analyses.
    """
    
    resolution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_id: str = ""
    strategy_used: ResolutionStrategy = ResolutionStrategy.AUTOMATIC_VOTING
    
    # Resolution outcome
    success: bool = False
    resolved_value: Any = None
    confidence: float = field(default=0.0)
    
    # Process information
    resolution_time_ms: float = 0.0
    attempts_made: int = 1
    rationale: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolver_id: str = ""
    
    def __post_init__(self):
        """Validate resolution data after initialization."""
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this resolution has high confidence."""
        return self.success and self.confidence >= threshold
    
    def is_fast_resolution(self, max_time_ms: float = 100.0) -> bool:
        """Check if this was a fast resolution."""
        return self.resolution_time_ms <= max_time_ms
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the resolution result."""
        return {
            'resolution_id': self.resolution_id,
            'conflict_id': self.conflict_id,
            'strategy': self.strategy_used.value,
            'success': self.success,
            'confidence': self.confidence,
            'time_ms': self.resolution_time_ms,
            'attempts': self.attempts_made,
            'high_confidence': self.is_high_confidence(),
        }