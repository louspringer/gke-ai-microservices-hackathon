#!/usr/bin/env python3
"""
Comprehensive test suite for Beast Mode Framework core implementation.

This test validates the implementation of the core Beast Mode components
according to the task requirements in the DAG implementation plan.
"""

import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, 'src')

from beast_mode import (
    ReflectiveModule, ModuleStatus, HealthIndicator,
    ToolHealthDiagnostics, PDCACore, PDCAPhase, PDCACycle,
    RCAEngine, RCAPattern, RCAResult,
    StakeholderDrivenMultiPerspectiveEngine,
    StakeholderType, DecisionContext, MultiStakeholderAnalysis
)


def test_reflective_module_base():
    """Test ReflectiveModule base class functionality."""
    print("Testing ReflectiveModule base class...")
    
    # Create a simple implementation for testing
    class TestModule(ReflectiveModule):
        def get_module_status(self):
            return ModuleStatus.HEALTHY
        
        def is_healthy(self):
            return True
        
        def get_health_indicators(self):
            return [HealthIndicator(
                name="test_indicator",
                status="healthy",
                message="Test module is healthy"
            )]
        
        def get_operational_info(self):
            return {
                'module_type': 'TestModule',
                'test_data': 'working'
            }
    
    module = TestModule()
    
    # Test basic functionality
    assert module.is_healthy() == True
    assert module.get_module_status() == ModuleStatus.HEALTHY
    assert len(module.get_health_indicators()) == 1
    assert module.get_operational_info()['module_type'] == 'TestModule'
    
    # Test interface validation
    validation = module.validate_interface_compliance()
    assert validation['interface_compliance'] == True
    assert len(validation['missing_methods']) == 0
    
    print("✅ ReflectiveModule base class tests passed")


def test_tool_health_diagnostics():
    """Test ToolHealthDiagnostics implementation."""
    print("Testing ToolHealthDiagnostics...")
    
    diagnostics = ToolHealthDiagnostics()
    
    # Test module health
    assert diagnostics.is_healthy() == True
    assert diagnostics.get_module_status() == ModuleStatus.HEALTHY
    
    # Test tool registration
    diagnostics.register_tool('test_tool', {'version': '1.0'})
    
    # Test diagnosis
    error_context = {
        'error_message': 'command not found: test_tool',
        'exit_code': 127
    }
    
    result = diagnostics.diagnose_tool_failure('test_tool', error_context)
    assert result.tool_name == 'test_tool'
    assert result.status is not None
    assert len(result.repair_suggestions) > 0
    
    # Test repair
    repair_result = diagnostics.repair_tool_systematically(result)
    assert repair_result.tool_name == 'test_tool'
    assert repair_result.repair_attempted is not None
    
    # Test prevention patterns
    patterns = diagnostics.get_prevention_patterns('test_tool')
    assert len(patterns) > 0
    
    print("✅ ToolHealthDiagnostics tests passed")


def test_pdca_core():
    """Test PDCACore implementation."""
    print("Testing PDCACore...")
    
    pdca = PDCACore()
    
    # Test module health
    assert pdca.is_healthy() == True
    assert pdca.get_module_status() == ModuleStatus.HEALTHY
    
    # Test cycle creation
    cycle = pdca.create_cycle("Test Cycle", "Testing PDCA implementation")
    assert cycle.title == "Test Cycle"
    assert cycle.status.value == "initialized"
    
    # Test cycle start
    success = pdca.start_cycle(cycle.cycle_id)
    assert success == True
    assert cycle.status.value == "in_progress"
    
    # Test phase execution
    def plan_executor(cycle):
        from beast_mode.pdca.pdca_core import PDCAPhaseResult, PDCAPhase
        return PDCAPhaseResult(
            phase=PDCAPhase.PLAN,
            success=True,
            message="Planning completed successfully"
        )
    
    plan_result = pdca.execute_plan_phase(cycle.cycle_id, plan_executor)
    assert plan_result.success == True
    assert plan_result.phase == PDCAPhase.PLAN
    
    # Test cycle retrieval
    retrieved_cycle = pdca.get_cycle(cycle.cycle_id)
    assert retrieved_cycle is not None
    assert retrieved_cycle.cycle_id == cycle.cycle_id
    
    print("✅ PDCACore tests passed")


def test_rca_engine():
    """Test RCAEngine implementation."""
    print("Testing RCAEngine...")
    
    rca = RCAEngine()
    
    # Test module health
    assert rca.is_healthy() == True
    assert rca.get_module_status() == ModuleStatus.HEALTHY
    
    # Test root cause analysis
    symptoms = ["command not found", "docker daemon not running"]
    context = {"tool": "docker", "environment": "development"}
    
    result = rca.analyze_root_cause(
        "Docker command failing",
        symptoms,
        context
    )
    
    assert result.problem_description == "Docker command failing"
    assert len(result.symptoms) == 2
    assert result.analysis_id is not None
    
    # Test pattern matching (should find Docker-related patterns)
    if result.identified_patterns:
        pattern = result.identified_patterns[0]
        assert pattern.name is not None
        assert len(pattern.systematic_fixes) > 0
    
    # Test systematic fix implementation
    if result.systematic_fixes:
        fix_result = rca.implement_systematic_fix(result, 0)
        assert 'success' in fix_result
        assert 'message' in fix_result
    
    # Test pattern statistics
    stats = rca.get_pattern_statistics()
    assert 'total_patterns' in stats
    assert stats['total_patterns'] > 0
    
    print("✅ RCAEngine tests passed")


def test_multi_perspective_engine():
    """Test StakeholderDrivenMultiPerspectiveEngine implementation."""
    print("Testing StakeholderDrivenMultiPerspectiveEngine...")
    
    engine = StakeholderDrivenMultiPerspectiveEngine()
    
    # Test module health
    assert engine.is_healthy() == True
    assert engine.get_module_status() == ModuleStatus.HEALTHY
    
    # Create decision context
    decision_context = DecisionContext(
        title="Test Architecture Decision",
        description="Testing multi-perspective analysis",
        decision_type="architecture"
    )
    
    # Test low confidence analysis
    analysis = engine.analyze_low_percentage_decision(decision_context, 0.3)
    
    assert analysis.decision_context.title == "Test Architecture Decision"
    assert len(analysis.perspectives) > 0
    assert analysis.is_complete() == True
    
    # Test individual perspective methods
    beast_perspective = engine.beast_mode_perspective(decision_context)
    assert beast_perspective.stakeholder_type == StakeholderType.BEAST_MODE
    assert len(beast_perspective.concerns) > 0
    assert len(beast_perspective.recommendations) > 0
    
    gke_perspective = engine.gke_consumer_perspective(decision_context)
    assert gke_perspective.stakeholder_type == StakeholderType.GKE_CONSUMER
    
    dev_perspective = engine.developer_perspective(decision_context)
    assert dev_perspective.stakeholder_type == StakeholderType.DEVELOPER
    
    # Test perspective synthesis
    synthesis = engine.synthesize_stakeholder_perspectives(analysis)
    assert synthesis['synthesis_success'] == True
    assert 'consensus_level' in synthesis
    assert 'recommended_outcome' in synthesis
    
    print("✅ StakeholderDrivenMultiPerspectiveEngine tests passed")


def test_integration_workflow():
    """Test integration between components."""
    print("Testing component integration...")
    
    # Create components
    diagnostics = ToolHealthDiagnostics()
    pdca = PDCACore()
    rca = RCAEngine()
    multi_perspective = StakeholderDrivenMultiPerspectiveEngine()
    
    # Test integrated workflow: Problem -> RCA -> PDCA -> Multi-perspective
    
    # 1. Diagnose a problem
    error_context = {'error_message': 'docker: command not found'}
    diagnostic_result = diagnostics.diagnose_tool_failure('docker', error_context)
    
    # 2. Perform RCA
    rca_result = rca.analyze_root_cause(
        "Docker installation issue",
        [diagnostic_result.message],
        {'diagnostic_result': diagnostic_result.details}
    )
    
    # 3. Create PDCA cycle for resolution
    cycle = pdca.create_cycle(
        "Resolve Docker Issue",
        f"Systematic resolution of: {rca_result.problem_description}"
    )
    
    # Add RCA findings to cycle context
    cycle.context['rca_result'] = rca_result.get_summary()
    cycle.add_objective("Implement systematic fix for Docker issue")
    
    # 4. If confidence is low, use multi-perspective analysis
    if rca_result.confidence_level < 0.5:
        decision_context = DecisionContext(
            title="Docker Resolution Strategy",
            description="Determine best approach for Docker issue resolution",
            decision_type="implementation"
        )
        
        mp_analysis = multi_perspective.analyze_low_percentage_decision(decision_context, 0.3)
        cycle.context['multi_perspective_analysis'] = mp_analysis.get_analysis_summary()
    
    # Verify integration
    assert cycle.context['rca_result']['analysis_id'] == rca_result.analysis_id
    assert diagnostic_result.tool_name == 'docker'
    
    print("✅ Component integration tests passed")


def test_performance_requirements():
    """Test performance requirements from the tasks."""
    print("Testing performance requirements...")
    
    # Test RCA engine <1s response time
    rca = RCAEngine()
    start_time = time.time()
    
    result = rca.analyze_root_cause(
        "Performance test",
        ["test symptom"],
        {"test": "context"}
    )
    
    analysis_time = time.time() - start_time
    assert analysis_time < 1.0, f"RCA analysis took {analysis_time:.3f}s, should be <1s"
    
    # Test diagnostics <1s response time
    diagnostics = ToolHealthDiagnostics()
    start_time = time.time()
    
    diagnostic_result = diagnostics.diagnose_tool_failure(
        'test_tool',
        {'error_message': 'test error'}
    )
    
    diagnosis_time = time.time() - start_time
    assert diagnosis_time < 1.0, f"Diagnosis took {diagnosis_time:.3f}s, should be <1s"
    
    print("✅ Performance requirements tests passed")


def run_comprehensive_test():
    """Run all tests and report results."""
    print("🚀 Starting Beast Mode Framework Core Implementation Tests")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Run all test functions
        test_reflective_module_base()
        test_tool_health_diagnostics()
        test_pdca_core()
        test_rca_engine()
        test_multi_perspective_engine()
        test_integration_workflow()
        test_performance_requirements()
        
        total_time = time.time() - start_time
        
        print("=" * 60)
        print(f"🎉 ALL TESTS PASSED! Total time: {total_time:.2f}s")
        print()
        print("✅ CORE-2: Tool Health Diagnostics Engine - IMPLEMENTED")
        print("✅ CORE-3: PDCA Core Interface - IMPLEMENTED") 
        print("✅ CORE-4: RCA Engine Interface - IMPLEMENTED")
        print("✅ PERSPECTIVE-1: Stakeholder-Driven Multi-Perspective Engine - IMPLEMENTED")
        print()
        print("🎯 Beast Mode Framework core components are ready for systematic excellence!")
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)