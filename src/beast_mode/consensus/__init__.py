"""
Multi-Agent Consensus Engine - Beast Mode Framework

A systematic consensus engine that resolves conflicts between multiple agents
through proven consensus algorithms, confidence scoring, and decision orchestration.

This module provides:
- Systematic consensus mechanisms for multi-agent systems
- Confidence scoring based on analysis quality and consistency
- Decision orchestration for complex multi-agent workflows
- Conflict resolution with automatic and escalation strategies
"""

from .core.consensus_engine import ConsensusEngine
from .models.data_models import (
    AgentAnalysis,
    ConsensusResult,
    DecisionWorkflow,
    ConflictInfo,
    ResolutionResult
)
__version__ = "1.0.0"
__all__ = [
    "ConsensusEngine",
    "AgentAnalysis",
    "ConsensusResult", 
    "DecisionWorkflow",
    "ConflictInfo",
    "ResolutionResult",
]