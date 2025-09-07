"""
Enhanced Project Registry Intelligence Engine for Beast Mode Framework

This module provides comprehensive project registry intelligence with full 69 requirements
and 100 domains integration, multi-perspective analysis, and systematic decision support.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..core.reflective_module import ReflectiveModule
from ..framework.data_models import MultiStakeholderAnalysis, StakeholderPerspective, ModelDrivenDecisionResult


logger = logging.getLogger(__name__)


@dataclass
class DomainInfo:
    """Information about a domain in the project registry"""
    name: str
    description: str
    domain_type: str
    compliance_status: str
    requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    testing_status: str = "unknown"
    documentation_status: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'domain_type': self.domain_type,
            'compliance_status': self.compliance_status,
            'requirements': self.requirements,
            'dependencies': self.dependencies,
            'tools': self.tools,
            'testing_status': self.testing_status,
            'documentation_status': self.documentation_status
        }


@dataclass
class RequirementInfo:
    """Information about a requirement in the project registry"""
    id: str
    description: str
    domain: str
    implementation: str
    test: str
    priority: str = "medium"
    status: str = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'description': self.description,
            'domain': self.domain,
            'implementation': self.implementation,
            'test': self.test,
            'priority': self.priority,
            'status': self.status
        }


@dataclass
class IntelligenceInsight:
    """Intelligence insight from registry analysis"""
    insight_type: str
    confidence: float
    description: str
    recommendations: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'insight_type': self.insight_type,
            'confidence': self.confidence,
            'description': self.description,
            'recommendations': self.recommendations,
            'evidence': self.evidence,
            'timestamp': self.timestamp.isoformat()
        }


class ProjectRegistryIntelligenceEngine(ReflectiveModule):
    """
    Enhanced Project Registry Intelligence Engine with comprehensive capabilities.
    
    Provides:
    - Full 69 requirements integration and analysis
    - 100 domains management and intelligence
    - Multi-perspective decision support
    - Systematic pattern recognition and recommendations
    """
    
    def __init__(self, registry_path: str = "project_model_registry.json"):
        super().__init__()
        self.registry_path = Path(registry_path)
        self.registry_data: Dict[str, Any] = {}
        self.domains: Dict[str, DomainInfo] = {}
        self.requirements: Dict[str, RequirementInfo] = {}
        self.insights_cache: List[IntelligenceInsight] = []
        
        # Intelligence configuration
        self.confidence_threshold = 0.7
        self.max_insights_cache = 1000
        
        # Load registry data
        self._load_registry_data()
        self._parse_domains()
        self._parse_requirements()
        
        logger.info(f"Initialized Project Registry Intelligence Engine with {len(self.domains)} domains and {len(self.requirements)} requirements")
    
    def _load_registry_data(self) -> None:
        """Load project registry data from JSON file"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    self.registry_data = json.load(f)
                logger.info(f"Loaded registry data from {self.registry_path}")
            else:
                logger.warning(f"Registry file not found: {self.registry_path}")
                self.registry_data = {}
        except Exception as e:
            logger.error(f"Failed to load registry data: {e}")
            self.registry_data = {}
    
    def _parse_domains(self) -> None:
        """Parse domain information from registry data"""
        domain_arch = self.registry_data.get('domain_architecture', {})
        
        # Parse domain categories
        for category_name, category_data in domain_arch.items():
            if isinstance(category_data, dict) and 'domains' in category_data:
                domains_list = category_data['domains']
                if isinstance(domains_list, list):
                    for domain_name in domains_list:
                        domain_info = DomainInfo(
                            name=domain_name,
                            description=category_data.get('description', ''),
                            domain_type=category_name,
                            compliance_status=category_data.get('compliance', 'unknown'),
                            testing_status=category_data.get('testing', 'unknown'),
                            documentation_status=category_data.get('documentation', 'unknown')
                        )
                        self.domains[domain_name] = domain_info
        
        logger.info(f"Parsed {len(self.domains)} domains from registry")
    
    def _parse_requirements(self) -> None:
        """Parse requirements information from registry data"""
        requirements_data = self.registry_data.get('requirements', {})
        
        for req_id, req_data in requirements_data.items():
            if isinstance(req_data, dict):
                requirement_info = RequirementInfo(
                    id=req_id,
                    description=req_data.get('requirement', ''),
                    domain=req_data.get('domain', 'unknown'),
                    implementation=req_data.get('implementation', ''),
                    test=req_data.get('test', ''),
                    priority=req_data.get('priority', 'medium'),
                    status=req_data.get('status', 'pending')
                )
                self.requirements[req_id] = requirement_info
        
        logger.info(f"Parsed {len(self.requirements)} requirements from registry")
    
    def analyze_domain_coverage(self) -> IntelligenceInsight:
        """Analyze domain coverage and completeness"""
        total_domains = len(self.domains)
        compliant_domains = sum(1 for d in self.domains.values() if d.compliance_status == 'RM compliant')
        tested_domains = sum(1 for d in self.domains.values() if d.testing_status in ['complete', 'comprehensive'])
        documented_domains = sum(1 for d in self.domains.values() if d.documentation_status == 'complete')
        
        coverage_score = (compliant_domains + tested_domains + documented_domains) / (total_domains * 3)
        
        recommendations = []
        if coverage_score < 0.8:
            recommendations.append("Improve domain compliance, testing, and documentation")
        if compliant_domains < total_domains:
            recommendations.append(f"Make {total_domains - compliant_domains} domains RM compliant")
        if tested_domains < total_domains:
            recommendations.append(f"Add comprehensive testing to {total_domains - tested_domains} domains")
        
        insight = IntelligenceInsight(
            insight_type="domain_coverage",
            confidence=0.95,
            description=f"Domain coverage analysis: {coverage_score:.1%} overall completion",
            recommendations=recommendations,
            evidence={
                'total_domains': total_domains,
                'compliant_domains': compliant_domains,
                'tested_domains': tested_domains,
                'documented_domains': documented_domains,
                'coverage_score': coverage_score
            }
        )
        
        self._cache_insight(insight)
        return insight
    
    def analyze_requirements_status(self) -> IntelligenceInsight:
        """Analyze requirements implementation status"""
        total_requirements = len(self.requirements)
        implemented_requirements = sum(1 for r in self.requirements.values() if r.status == 'implemented')
        tested_requirements = sum(1 for r in self.requirements.values() if r.test and r.test != '')
        
        implementation_rate = implemented_requirements / total_requirements if total_requirements > 0 else 0
        testing_rate = tested_requirements / total_requirements if total_requirements > 0 else 0
        
        recommendations = []
        if implementation_rate < 0.8:
            recommendations.append(f"Implement {total_requirements - implemented_requirements} pending requirements")
        if testing_rate < 0.9:
            recommendations.append(f"Add tests for {total_requirements - tested_requirements} requirements")
        
        insight = IntelligenceInsight(
            insight_type="requirements_status",
            confidence=0.9,
            description=f"Requirements status: {implementation_rate:.1%} implemented, {testing_rate:.1%} tested",
            recommendations=recommendations,
            evidence={
                'total_requirements': total_requirements,
                'implemented_requirements': implemented_requirements,
                'tested_requirements': tested_requirements,
                'implementation_rate': implementation_rate,
                'testing_rate': testing_rate
            }
        )
        
        self._cache_insight(insight)
        return insight
    
    def identify_domain_dependencies(self) -> IntelligenceInsight:
        """Identify and analyze domain dependencies"""
        dependency_graph = {}
        circular_dependencies = []
        
        # Build dependency graph
        for domain_name, domain_info in self.domains.items():
            dependency_graph[domain_name] = domain_info.dependencies
        
        # Detect circular dependencies (simplified check)
        for domain, deps in dependency_graph.items():
            for dep in deps:
                if dep in dependency_graph and domain in dependency_graph[dep]:
                    circular_dependencies.append((domain, dep))
        
        recommendations = []
        if circular_dependencies:
            recommendations.append(f"Resolve {len(circular_dependencies)} circular dependencies")
        
        # Identify domains with many dependencies (potential bottlenecks)
        high_dependency_domains = [
            domain for domain, deps in dependency_graph.items() 
            if len(deps) > 5
        ]
        
        if high_dependency_domains:
            recommendations.append(f"Review high-dependency domains: {', '.join(high_dependency_domains)}")
        
        insight = IntelligenceInsight(
            insight_type="domain_dependencies",
            confidence=0.85,
            description=f"Dependency analysis: {len(circular_dependencies)} circular dependencies found",
            recommendations=recommendations,
            evidence={
                'dependency_graph': dependency_graph,
                'circular_dependencies': circular_dependencies,
                'high_dependency_domains': high_dependency_domains
            }
        )
        
        self._cache_insight(insight)
        return insight
    
    def recommend_implementation_priority(self) -> IntelligenceInsight:
        """Recommend implementation priority based on dependencies and impact"""
        priority_scores = {}
        
        for req_id, req_info in self.requirements.items():
            score = 0
            
            # Priority weight
            priority_weights = {'high': 3, 'medium': 2, 'low': 1}
            score += priority_weights.get(req_info.priority, 1)
            
            # Domain importance (demo_core domains get higher priority)
            domain_info = self.domains.get(req_info.domain)
            if domain_info and domain_info.domain_type == 'demo_core':
                score += 2
            
            # Implementation status
            if req_info.status == 'pending':
                score += 1
            elif req_info.status == 'in_progress':
                score += 0.5
            
            priority_scores[req_id] = score
        
        # Sort by priority score
        sorted_requirements = sorted(
            priority_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        top_priorities = sorted_requirements[:10]
        
        recommendations = [
            f"Prioritize requirement {req_id}: {self.requirements[req_id].description[:50]}..."
            for req_id, _ in top_priorities[:5]
        ]
        
        insight = IntelligenceInsight(
            insight_type="implementation_priority",
            confidence=0.8,
            description=f"Implementation priority analysis for {len(self.requirements)} requirements",
            recommendations=recommendations,
            evidence={
                'priority_scores': dict(sorted_requirements[:20]),
                'top_priorities': [req_id for req_id, _ in top_priorities]
            }
        )
        
        self._cache_insight(insight)
        return insight
    
    def escalate_to_multi_perspective(self, decision_context: str, confidence: float) -> MultiStakeholderAnalysis:
        """
        Escalate low-confidence decisions to multi-perspective analysis.
        
        Integrates with R12 multi-perspective decision support for decisions
        with confidence < 50% or complex domain interactions.
        """
        if confidence >= 0.5:
            logger.info(f"Decision confidence {confidence:.1%} above threshold, no escalation needed")
            return None
        
        logger.info(f"Escalating decision to multi-perspective analysis (confidence: {confidence:.1%})")
        
        # Analyze from different stakeholder perspectives
        perspectives = []
        
        # Beast Mode perspective (systematic excellence)
        beast_mode_perspective = StakeholderPerspective(
            stakeholder_type="beast_mode_framework",
            confidence_level=0.9,
            decision_factors=[
                "Systematic approach alignment",
                "PDCA cycle integration",
                "Quality assurance standards",
                "Performance optimization"
            ],
            risk_assessment="Low risk with systematic approach",
            recommendations=[
                "Apply systematic methodology",
                "Implement comprehensive testing",
                "Use PDCA for continuous improvement"
            ]
        )
        perspectives.append(beast_mode_perspective)
        
        # Technical Architecture perspective
        tech_perspective = StakeholderPerspective(
            stakeholder_type="technical_architect",
            confidence_level=0.8,
            decision_factors=[
                "Domain architecture compliance",
                "Dependency management",
                "Scalability considerations",
                "Integration complexity"
            ],
            risk_assessment="Medium risk due to complexity",
            recommendations=[
                "Review domain boundaries",
                "Validate dependency graph",
                "Plan for scalability"
            ]
        )
        perspectives.append(tech_perspective)
        
        # Project Management perspective
        pm_perspective = StakeholderPerspective(
            stakeholder_type="project_manager",
            confidence_level=0.7,
            decision_factors=[
                "Timeline impact",
                "Resource allocation",
                "Risk mitigation",
                "Deliverable quality"
            ],
            risk_assessment="Medium risk to timeline",
            recommendations=[
                "Prioritize critical path items",
                "Allocate additional resources",
                "Implement risk mitigation"
            ]
        )
        perspectives.append(pm_perspective)
        
        # Quality Assurance perspective
        qa_perspective = StakeholderPerspective(
            stakeholder_type="quality_assurance",
            confidence_level=0.85,
            decision_factors=[
                "Testing coverage",
                "Compliance validation",
                "Documentation quality",
                "Error handling"
            ],
            risk_assessment="Low risk with proper testing",
            recommendations=[
                "Implement comprehensive test suite",
                "Validate compliance requirements",
                "Document all decisions"
            ]
        )
        perspectives.append(qa_perspective)
        
        # Create multi-stakeholder analysis
        analysis = MultiStakeholderAnalysis(
            decision_context=decision_context,
            stakeholder_perspectives=perspectives,
            consensus_confidence=sum(p.confidence_level for p in perspectives) / len(perspectives),
            risk_factors=[
                "Implementation complexity",
                "Domain integration challenges",
                "Timeline constraints",
                "Quality requirements"
            ],
            mitigation_strategies=[
                "Systematic implementation approach",
                "Comprehensive testing strategy",
                "Regular progress reviews",
                "Risk monitoring and adjustment"
            ]
        )
        
        logger.info(f"Multi-perspective analysis complete with consensus confidence: {analysis.consensus_confidence:.1%}")
        return analysis
    
    def get_domain_intelligence(self, domain_name: str) -> Dict[str, Any]:
        """Get comprehensive intelligence about a specific domain"""
        domain_info = self.domains.get(domain_name)
        if not domain_info:
            return {'error': f'Domain {domain_name} not found'}
        
        # Get related requirements
        related_requirements = [
            req for req in self.requirements.values() 
            if req.domain == domain_name
        ]
        
        # Analyze domain health
        health_score = 0
        if domain_info.compliance_status == 'RM compliant':
            health_score += 0.4
        if domain_info.testing_status in ['complete', 'comprehensive']:
            health_score += 0.3
        if domain_info.documentation_status == 'complete':
            health_score += 0.3
        
        return {
            'domain_info': domain_info.to_dict(),
            'related_requirements': [req.to_dict() for req in related_requirements],
            'health_score': health_score,
            'recommendations': self._generate_domain_recommendations(domain_info, related_requirements)
        }
    
    def _generate_domain_recommendations(self, domain_info: DomainInfo, requirements: List[RequirementInfo]) -> List[str]:
        """Generate recommendations for a specific domain"""
        recommendations = []
        
        if domain_info.compliance_status != 'RM compliant':
            recommendations.append("Implement ReflectiveModule compliance")
        
        if domain_info.testing_status not in ['complete', 'comprehensive']:
            recommendations.append("Add comprehensive testing suite")
        
        if domain_info.documentation_status != 'complete':
            recommendations.append("Complete documentation")
        
        pending_requirements = [req for req in requirements if req.status == 'pending']
        if pending_requirements:
            recommendations.append(f"Implement {len(pending_requirements)} pending requirements")
        
        return recommendations
    
    def _cache_insight(self, insight: IntelligenceInsight) -> None:
        """Cache intelligence insight for future reference"""
        self.insights_cache.append(insight)
        
        # Maintain cache size limit
        if len(self.insights_cache) > self.max_insights_cache:
            self.insights_cache = self.insights_cache[-self.max_insights_cache:]
    
    def get_cached_insights(self, insight_type: Optional[str] = None) -> List[IntelligenceInsight]:
        """Get cached insights, optionally filtered by type"""
        if insight_type:
            return [insight for insight in self.insights_cache if insight.insight_type == insight_type]
        return self.insights_cache.copy()
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence report"""
        domain_coverage = self.analyze_domain_coverage()
        requirements_status = self.analyze_requirements_status()
        dependencies = self.identify_domain_dependencies()
        priorities = self.recommend_implementation_priority()
        
        return {
            'summary': {
                'total_domains': len(self.domains),
                'total_requirements': len(self.requirements),
                'analysis_timestamp': datetime.utcnow().isoformat()
            },
            'domain_coverage': domain_coverage.to_dict(),
            'requirements_status': requirements_status.to_dict(),
            'dependencies_analysis': dependencies.to_dict(),
            'implementation_priorities': priorities.to_dict(),
            'overall_health_score': self._calculate_overall_health_score()
        }
    
    def _calculate_overall_health_score(self) -> float:
        """Calculate overall project health score"""
        if not self.domains or not self.requirements:
            return 0.0
        
        # Domain health
        compliant_domains = sum(1 for d in self.domains.values() if d.compliance_status == 'RM compliant')
        domain_score = compliant_domains / len(self.domains)
        
        # Requirements health
        implemented_requirements = sum(1 for r in self.requirements.values() if r.status == 'implemented')
        requirements_score = implemented_requirements / len(self.requirements)
        
        # Weighted average
        return (domain_score * 0.6) + (requirements_score * 0.4)
    
    # ReflectiveModule implementation
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the registry intelligence engine"""
        return {
            'status': 'healthy',
            'domains_loaded': len(self.domains),
            'requirements_loaded': len(self.requirements),
            'insights_cached': len(self.insights_cache),
            'registry_file_exists': self.registry_path.exists(),
            'last_analysis': datetime.utcnow().isoformat()
        }
    
    async def perform_self_diagnosis(self) -> Dict[str, Any]:
        """Perform self-diagnosis of registry intelligence capabilities"""
        issues = []
        
        if not self.registry_path.exists():
            issues.append("Registry file not found")
        
        if len(self.domains) == 0:
            issues.append("No domains loaded")
        
        if len(self.requirements) == 0:
            issues.append("No requirements loaded")
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'capabilities': [
                'Domain analysis',
                'Requirements tracking',
                'Dependency analysis',
                'Multi-perspective escalation',
                'Intelligence insights'
            ]
        }
    
    def get_operational_metrics(self) -> Dict[str, Any]:
        """Get operational metrics for monitoring"""
        return {
            'domains_count': len(self.domains),
            'requirements_count': len(self.requirements),
            'insights_generated': len(self.insights_cache),
            'overall_health_score': self._calculate_overall_health_score(),
            'registry_file_size': self.registry_path.stat().st_size if self.registry_path.exists() else 0
        }