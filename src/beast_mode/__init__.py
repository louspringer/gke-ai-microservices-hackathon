"""
Beast Mode Framework - Systematic Excellence for Development Operations.

This framework provides systematic approaches to development, deployment,
and operational excellence, implementing proven methodologies that deliver
superior outcomes compared to ad-hoc approaches.
"""

from .core.reflective_module import ReflectiveModule, ModuleStatus, HealthIndicator
from .framework.data_models import (
    StakeholderType, StakeholderPerspective, DecisionContext,
    MultiStakeholderAnalysis, ModelDrivenDecisionResult
)
from .diagnostics.tool_health_diagnostics import ToolHealthDiagnostics
from .pdca.pdca_core import PDCACore, PDCAPhase, PDCACycle
from .rca.rca_engine import RCAEngine, RCAPattern, RCAResult
from .multi_perspective.stakeholder_engine import StakeholderDrivenMultiPerspectiveEngine

__version__ = "0.1.0"

__all__ = [
    # Core framework
    'ReflectiveModule',
    'ModuleStatus', 
    'HealthIndicator',
    
    # Data models
    'StakeholderType',
    'StakeholderPerspective',
    'DecisionContext',
    'MultiStakeholderAnalysis',
    'ModelDrivenDecisionResult',
    
    # Core engines
    'ToolHealthDiagnostics',
    'PDCACore',
    'PDCAPhase',
    'PDCACycle',
    'RCAEngine',
    'RCAPattern',
    'RCAResult',
    'StakeholderDrivenMultiPerspectiveEngine',
]