#!/usr/bin/env python3
"""
Beast Mode Core Validation Test

Simplified validation focusing on core Beast Mode components
without external dependencies.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Beast Mode Core Components
from src.beast_mode.core.reflective_module import ReflectiveModule, ModuleStatus
from src.beast_mode.system.beast_mode_system_orchestrator import BeastModeSystemOrchestrator
from src.beast_mode.pdca.pdca_orchestrator import PDCAOrchestrator, OrchestrationStrategy
from src.beast_mode.agent_network.core.network_coordinator import NetworkCoordinator
from src.beast_mode.agent_network.intelligence.network_intelligence_engine import NetworkIntelligenceEngine
from src.beast_mode.consensus.core.consensus_engine import ConsensusEngine
from src.beast_mode.rca.rca_engine import RCAEngine
from src.beast_mode.diagnostics.tool_health_diagnostics import ToolHealthDiagnostics

# Agent Network Models
from src.beast_mode.agent_network.models.data_models import AgentNetworkState, AgentInfo

# Systematic Secrets Management
from src.beast_mode.systematic_secrets.core.secrets_manager import SecretsManager
from src.beast_mode.systematic_secrets.models.secret import Secret
from src.beast_mode.systematic_secrets.models.environment import Environment


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BeastModeCoreValidator:
    """
    Core validation for the Beast Mode ecosystem.
    
    Validates core functionality without external dependencies.
    """
    
    def __init__(self):
        self.validation_results = {}
        self.performance_metrics = {}
        self.start_time = None
        
    async def run_core_validation(self) -> Dict[str, Any]:
        """
        Run core Beast Mode validation.
        
        Returns:
            Complete validation results with performance metrics
        """
        logger.info("🚀 Starting Beast Mode Core Validation")
        self.start_time = time.time()
        
        try:
            # Phase 1: Component Health Validation
            await self._validate_component_health()
            
            # Phase 2: System Orchestration
            await self._validate_system_orchestration()
            
            # Phase 3: PDCA Orchestration
            await self._validate_pdca_orchestration()
            
            # Phase 4: Agent Network
            await self._validate_agent_network()
            
            # Phase 5: Consensus Engine
            await self._validate_consensus_engine()
            
            # Phase 6: Secrets Management
            await self._validate_secrets_management()
            
            # Phase 7: Performance Benchmarks
            await self._validate_performance()
            
            # Generate final report
            return await self._generate_validation_report()
            
        except Exception as e:
            logger.error(f"Core validation failed: {e}")
            return {
                'validation_status': 'FAILED',
                'error': str(e),
                'completed_phases': list(self.validation_results.keys())
            }
    
    async def _validate_component_health(self):
        """Validate core component health"""
        logger.info("📋 Phase 1: Component Health Validation")
        
        phase_results = {
            'phase': 'component_health',
            'status': 'running',
            'components': {}
        }
        
        try:
            # Test individual components
            components = {
                'network_coordinator': NetworkCoordinator(),
                'network_intelligence': NetworkIntelligenceEngine(),
                'consensus_engine': ConsensusEngine(),
                'rca_engine': RCAEngine(),
                'health_diagnostics': ToolHealthDiagnostics(),
                'secrets_manager': SecretsManager()
            }
            
            for name, component in components.items():
                try:
                    health_status = component.get_module_status()
                    health_indicators = component.get_health_indicators()
                    operational_info = component.get_operational_info()
                    
                    phase_results['components'][name] = {
                        'status': 'healthy' if component.is_healthy() else 'degraded',
                        'health_status': health_status.value,
                        'health_indicators': len(health_indicators),
                        'operational_info_available': bool(operational_info)
                    }
                    
                except Exception as e:
                    phase_results['components'][name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
            
            # Check overall health
            failed_components = [name for name, info in phase_results['components'].items() 
                               if info.get('status') == 'failed']
            
            if not failed_components:
                phase_results['status'] = 'PASSED'
                logger.info("✅ Component health validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_components'] = failed_components
                logger.error(f"❌ Component health FAILED: {failed_components}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ Component health validation failed: {e}")
        
        self.validation_results['component_health'] = phase_results
    
    async def _validate_system_orchestration(self):
        """Validate system orchestration"""
        logger.info("🔗 Phase 2: System Orchestration Validation")
        
        phase_results = {
            'phase': 'system_orchestration',
            'status': 'running',
            'orchestration_tests': {}
        }
        
        try:
            # Initialize system orchestrator
            orchestrator = BeastModeSystemOrchestrator()
            init_result = await orchestrator.initialize_system()
            
            phase_results['orchestration_tests']['initialization'] = {
                'status': 'PASSED' if init_result.get('initialization_status') == 'completed' else 'FAILED',
                'system_mode': init_result.get('system_mode'),
                'components_initialized': len(init_result.get('component_results', {}))
            }
            
            # Test system health assessment
            health_assessment = await orchestrator.assess_system_health()
            phase_results['orchestration_tests']['health_assessment'] = {
                'status': 'PASSED',
                'overall_status': health_assessment.overall_status.value,
                'component_count': len(health_assessment.component_health),
                'recommendations': len(health_assessment.recommendations)
            }
            
            # Test excellence cycle
            excellence_result = await orchestrator.execute_systematic_excellence_cycle()
            phase_results['orchestration_tests']['excellence_cycle'] = {
                'status': 'PASSED' if excellence_result.get('cycle_status') == 'completed' else 'FAILED',
                'cycle_duration': excellence_result.get('cycle_duration_seconds', 0)
            }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['orchestration_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ System orchestration validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ System orchestration FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ System orchestration validation failed: {e}")
        
        self.validation_results['system_orchestration'] = phase_results
    
    async def _validate_pdca_orchestration(self):
        """Validate PDCA orchestration"""
        logger.info("🔄 Phase 3: PDCA Orchestration Validation")
        
        phase_results = {
            'phase': 'pdca_orchestration',
            'status': 'running',
            'pdca_tests': {}
        }
        
        try:
            pdca_orchestrator = PDCAOrchestrator()
            
            # Register test components
            test_components = {
                'test_component_1': NetworkCoordinator(),
                'test_component_2': ConsensusEngine()
            }
            
            for name, component in test_components.items():
                pdca_orchestrator.register_component(name, component)
            
            # Test systematic improvement
            improvement_result = await pdca_orchestrator.orchestrate_systematic_improvement()
            phase_results['pdca_tests']['systematic_improvement'] = {
                'status': 'PASSED' if improvement_result.get('orchestration_insights') else 'FAILED',
                'strategy': improvement_result.get('strategy'),
                'planned_cycles': improvement_result.get('planned_cycles', 0),
                'execution_results': len(improvement_result.get('execution_results', []))
            }
            
            # Test different strategies
            from src.beast_mode.pdca.pdca_orchestrator import OrchestrationContext
            
            strategies = [OrchestrationStrategy.SEQUENTIAL, OrchestrationStrategy.PARALLEL]
            for strategy in strategies:
                try:
                    context = OrchestrationContext(
                        orchestration_id=f"test_{strategy.value}",
                        strategy=strategy,
                        max_concurrent_cycles=2
                    )
                    
                    strategy_result = await pdca_orchestrator.orchestrate_systematic_improvement(context)
                    phase_results['pdca_tests'][f'strategy_{strategy.value}'] = {
                        'status': 'PASSED',
                        'cycles_executed': len(strategy_result.get('execution_results', []))
                    }
                    
                except Exception as e:
                    phase_results['pdca_tests'][f'strategy_{strategy.value}'] = {
                        'status': 'FAILED',
                        'error': str(e)
                    }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['pdca_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ PDCA orchestration validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ PDCA orchestration FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ PDCA orchestration validation failed: {e}")
        
        self.validation_results['pdca_orchestration'] = phase_results
    
    async def _validate_agent_network(self):
        """Validate agent network coordination"""
        logger.info("🌐 Phase 4: Agent Network Validation")
        
        phase_results = {
            'phase': 'agent_network',
            'status': 'running',
            'network_tests': {}
        }
        
        try:
            network_coordinator = NetworkCoordinator()
            network_intelligence = NetworkIntelligenceEngine()
            
            # Test agent registration
            test_agents = ['agent_1', 'agent_2', 'agent_3']
            for agent_id in test_agents:
                registration_result = await network_coordinator.register_agent(agent_id, 'test_agent', {})
                if not registration_result:
                    raise Exception(f"Failed to register agent {agent_id}")
            
            phase_results['network_tests']['agent_registration'] = {
                'status': 'PASSED',
                'registered_agents': len(test_agents)
            }
            
            # Test coordination
            coordination_result = await network_coordinator.coordinate_agents(test_agents, 'round_robin')
            phase_results['network_tests']['coordination'] = {
                'status': 'PASSED' if coordination_result.get('coordination_successful') else 'FAILED',
                'coordinated_agents': len(coordination_result.get('coordinated_agents', []))
            }
            
            # Test intelligence analysis
            mock_network_state = AgentNetworkState(
                total_agents=len(test_agents),
                active_agents=[
                    AgentInfo(
                        agent_id=agent_id,
                        agent_type='test_agent',
                        status='active',
                        operations_count=10,
                        avg_response_time_ms=100.0
                    ) for agent_id in test_agents
                ],
                coordination_overhead_ms=50.0,
                error_rate=0.01
            )
            
            intelligence_result = await network_intelligence.analyze_network_performance(mock_network_state)
            phase_results['network_tests']['intelligence_analysis'] = {
                'status': 'PASSED',
                'health_score': intelligence_result.network_health_score,
                'patterns_identified': len(intelligence_result.identified_patterns)
            }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['network_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ Agent network validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ Agent network FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ Agent network validation failed: {e}")
        
        self.validation_results['agent_network'] = phase_results
    
    async def _validate_consensus_engine(self):
        """Validate consensus engine"""
        logger.info("🤝 Phase 5: Consensus Engine Validation")
        
        phase_results = {
            'phase': 'consensus_engine',
            'status': 'running',
            'consensus_tests': {}
        }
        
        try:
            consensus_engine = ConsensusEngine()
            
            # Test basic consensus
            test_agents = ['agent_1', 'agent_2', 'agent_3']
            decision_context = {
                'decision_type': 'test_decision',
                'options': ['option_a', 'option_b', 'option_c']
            }
            
            consensus_result = await consensus_engine.reach_consensus(test_agents, decision_context)
            phase_results['consensus_tests']['basic_consensus'] = {
                'status': 'PASSED' if consensus_result and consensus_result.consensus_reached else 'FAILED',
                'consensus_reached': consensus_result.consensus_reached if consensus_result else False,
                'confidence_score': consensus_result.confidence_score if consensus_result else 0.0
            }
            
            # Test performance
            start_time = time.time()
            performance_result = await consensus_engine.reach_consensus(test_agents, decision_context)
            consensus_time = (time.time() - start_time) * 1000
            
            phase_results['consensus_tests']['performance'] = {
                'status': 'PASSED' if consensus_time < 1000 else 'FAILED',
                'consensus_time_ms': consensus_time,
                'requirement_met': consensus_time < 1000
            }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['consensus_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ Consensus engine validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ Consensus engine FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ Consensus engine validation failed: {e}")
        
        self.validation_results['consensus_engine'] = phase_results
    
    async def _validate_secrets_management(self):
        """Validate secrets management"""
        logger.info("🔐 Phase 6: Secrets Management Validation")
        
        phase_results = {
            'phase': 'secrets_management',
            'status': 'running',
            'secrets_tests': {}
        }
        
        try:
            secrets_manager = SecretsManager()
            
            # Test environment creation
            test_env = Environment(
                name="test_environment",
                description="Test environment for validation",
                security_level="development"
            )
            
            env_result = await secrets_manager.create_environment(test_env)
            phase_results['secrets_tests']['environment_management'] = {
                'status': 'PASSED' if env_result else 'FAILED',
                'environment_created': bool(env_result)
            }
            
            # Test secret storage
            test_secret = Secret(
                name="test_secret",
                value="test_secret_value",
                environment="test_environment",
                secret_type="api_key",
                description="Test secret for validation"
            )
            
            store_result = await secrets_manager.store_secret(test_secret)
            phase_results['secrets_tests']['secret_storage'] = {
                'status': 'PASSED' if store_result else 'FAILED',
                'secret_stored': bool(store_result)
            }
            
            # Test secret retrieval
            retrieved_secret = await secrets_manager.get_secret("test_secret", "test_environment")
            phase_results['secrets_tests']['secret_retrieval'] = {
                'status': 'PASSED' if retrieved_secret else 'FAILED',
                'secret_retrieved': bool(retrieved_secret)
            }
            
            # Test health monitoring
            health_status = secrets_manager.get_module_status()
            phase_results['secrets_tests']['health_monitoring'] = {
                'status': 'PASSED',
                'health_status': health_status.value,
                'is_healthy': secrets_manager.is_healthy()
            }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['secrets_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ Secrets management validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ Secrets management FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ Secrets management validation failed: {e}")
        
        self.validation_results['secrets_management'] = phase_results
    
    async def _validate_performance(self):
        """Validate performance benchmarks"""
        logger.info("⚡ Phase 7: Performance Validation")
        
        phase_results = {
            'phase': 'performance',
            'status': 'running',
            'performance_tests': {}
        }
        
        try:
            # Benchmark 1: System initialization
            init_start = time.time()
            orchestrator = BeastModeSystemOrchestrator()
            await orchestrator.initialize_system()
            init_time = time.time() - init_start
            
            phase_results['performance_tests']['system_initialization'] = {
                'status': 'PASSED' if init_time < 10.0 else 'FAILED',
                'initialization_time_seconds': init_time,
                'requirement_met': init_time < 10.0
            }
            
            # Benchmark 2: PDCA cycle performance
            pdca_start = time.time()
            pdca_result = await orchestrator.pdca_orchestrator.orchestrate_systematic_improvement()
            pdca_time = time.time() - pdca_start
            
            phase_results['performance_tests']['pdca_cycle'] = {
                'status': 'PASSED' if pdca_time < 30.0 else 'FAILED',
                'cycle_time_seconds': pdca_time,
                'requirement_met': pdca_time < 30.0
            }
            
            # Benchmark 3: Consensus performance
            consensus_start = time.time()
            consensus_result = await orchestrator.consensus_engine.reach_consensus(
                ['agent_1', 'agent_2', 'agent_3'],
                {'test': 'performance_benchmark'}
            )
            consensus_time = (time.time() - consensus_start) * 1000
            
            phase_results['performance_tests']['consensus'] = {
                'status': 'PASSED' if consensus_time < 1000 else 'FAILED',
                'consensus_time_ms': consensus_time,
                'requirement_met': consensus_time < 1000
            }
            
            # Store performance metrics
            self.performance_metrics = {
                'system_initialization_time': init_time,
                'pdca_cycle_time': pdca_time,
                'consensus_time_ms': consensus_time
            }
            
            # Determine overall status
            failed_tests = [name for name, test in phase_results['performance_tests'].items() 
                          if test.get('status') == 'FAILED']
            
            if not failed_tests:
                phase_results['status'] = 'PASSED'
                logger.info("✅ Performance validation PASSED")
            else:
                phase_results['status'] = 'FAILED'
                phase_results['failed_tests'] = failed_tests
                logger.error(f"❌ Performance validation FAILED: {failed_tests}")
            
        except Exception as e:
            phase_results['status'] = 'FAILED'
            phase_results['error'] = str(e)
            logger.error(f"❌ Performance validation failed: {e}")
        
        self.validation_results['performance'] = phase_results
    
    async def _generate_validation_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        logger.info("📊 Generating validation report...")
        
        total_time = time.time() - self.start_time if self.start_time else 0
        
        # Calculate overall status
        phase_statuses = [phase.get('status') for phase in self.validation_results.values()]
        passed_phases = phase_statuses.count('PASSED')
        failed_phases = phase_statuses.count('FAILED')
        total_phases = len(phase_statuses)
        
        overall_status = 'PASSED' if failed_phases == 0 else 'PARTIAL' if passed_phases > failed_phases else 'FAILED'
        
        # Generate summary
        summary = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'total_validation_time_seconds': total_time,
            'overall_status': overall_status,
            'phase_summary': {
                'total_phases': total_phases,
                'passed_phases': passed_phases,
                'failed_phases': failed_phases,
                'success_rate': passed_phases / total_phases if total_phases > 0 else 0.0
            },
            'performance_metrics': self.performance_metrics
        }
        
        # Final report
        report = {
            'beast_mode_core_validation': {
                'summary': summary,
                'detailed_results': self.validation_results,
                'recommendations': self._generate_recommendations(overall_status)
            }
        }
        
        # Log final status
        if overall_status == 'PASSED':
            logger.info("🎉 Beast Mode Core Validation COMPLETED SUCCESSFULLY!")
            logger.info(f"✅ All {passed_phases} validation phases passed")
            logger.info(f"⚡ Total validation time: {total_time:.2f} seconds")
        else:
            logger.warning(f"⚠️ Beast Mode Core Validation completed with issues")
            logger.warning(f"✅ {passed_phases}/{total_phases} phases passed")
            logger.warning(f"❌ {failed_phases} phases failed")
        
        return report
    
    def _generate_recommendations(self, overall_status: str) -> List[str]:
        """Generate recommendations based on validation status"""
        
        if overall_status == 'PASSED':
            return [
                "🚀 Beast Mode core is ready for integration testing",
                "📋 Proceed with external system integration",
                "🔧 Set up production deployment configurations",
                "📊 Implement comprehensive monitoring"
            ]
        elif overall_status == 'PARTIAL':
            return [
                "🔧 Address failed validation phases",
                "🧪 Re-run validation after fixes",
                "📋 Focus on core functionality",
                "⚠️ Document known limitations"
            ]
        else:
            return [
                "🚨 Critical issues must be resolved",
                "🔍 Perform detailed debugging",
                "🧪 Implement comprehensive testing",
                "📋 Review system architecture"
            ]


async def main():
    """Main validation execution"""
    print("🧬 Beast Mode Core Validation Suite")
    print("=" * 50)
    
    validator = BeastModeCoreValidator()
    
    try:
        # Run core validation
        validation_report = await validator.run_core_validation()
        
        # Save report to file
        report_filename = f"beast_mode_core_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(validation_report, f, indent=2, default=str)
        
        print(f"\n📊 Validation report saved to: {report_filename}")
        
        # Print summary
        summary = validation_report['beast_mode_core_validation']['summary']
        print(f"\n🎯 VALIDATION SUMMARY:")
        print(f"   Overall Status: {summary['overall_status']}")
        print(f"   Success Rate: {summary['phase_summary']['success_rate']:.1%}")
        print(f"   Total Time: {summary['total_validation_time_seconds']:.2f}s")
        
        return validation_report
        
    except Exception as e:
        logger.error(f"Validation execution failed: {e}")
        return {'status': 'FAILED', 'error': str(e)}


if __name__ == "__main__":
    asyncio.run(main())