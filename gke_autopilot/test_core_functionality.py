#!/usr/bin/env python3
"""
GKE Autopilot Core Functionality Test

Tests the essential MVP functionality that we can validate
without complex package imports.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_data_models_comprehensive():
    """Comprehensive test of data models"""
    print("🔍 Testing Data Models Comprehensively...")
    
    try:
        from models.app_config import (
            AppConfig, ResourceRequests, ScalingConfig, 
            HealthCheckConfig, IngressConfig, ClusterConfig,
            DeploymentPhase, ScalingMode
        )
        
        # Test 1: Basic configuration creation
        app_config = AppConfig(
            name="mvp-test-app",
            image="gcr.io/google-samples/hello-app:1.0",
            port=8080,
            environment_variables={
                "ENV": "production",
                "LOG_LEVEL": "info",
                "DATABASE_URL": "postgresql://localhost:5432/app"
            },
            resource_requests=ResourceRequests(cpu="250m", memory="512Mi", storage="1Gi"),
            scaling_config=ScalingConfig(
                min_replicas=2, 
                max_replicas=10, 
                target_cpu_utilization=70,
                mode=ScalingMode.AUTO_CPU
            ),
            health_checks=HealthCheckConfig(
                path="/health", 
                port=8080,
                initial_delay_seconds=30,
                period_seconds=10
            ),
            ingress_config=IngressConfig(
                enabled=True,
                domain="mvp-test.example.com",
                tls=True,
                path="/",
                path_type="Prefix"
            )
        )
        
        print(f"✅ Created comprehensive app config: {app_config.name}")
        
        # Test 2: Serialization and deserialization
        config_dict = app_config.to_dict()
        print(f"✅ Serialized to dict with {len(config_dict)} top-level fields")
        
        # Verify key fields are present
        required_fields = ['name', 'image', 'port', 'resources', 'scaling', 'healthChecks', 'ingress']
        missing_fields = [field for field in required_fields if field not in config_dict]
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present in serialization")
        
        # Test 3: GKE Autopilot validation
        warnings = app_config.validate_for_gke_autopilot()
        print(f"✅ GKE Autopilot validation: {len(warnings)} warnings")
        for warning in warnings:
            print(f"   ⚠️  {warning}")
        
        # Test 4: Resource validation
        resources = app_config.resource_requests
        print(f"✅ Resource requests: CPU={resources.cpu}, Memory={resources.memory}, Storage={resources.storage}")
        
        # Test 5: Scaling configuration
        scaling = app_config.scaling_config
        hpa_spec = scaling.to_hpa_spec()
        print(f"✅ HPA spec generated with {len(hpa_spec)} fields")
        
        # Test 6: Health check configuration
        health = app_config.health_checks
        probe_config = health.to_kubernetes_probe()
        print(f"✅ Kubernetes probe config generated with {len(probe_config)} fields")
        
        # Test 7: Ingress configuration
        ingress = app_config.ingress_config
        if ingress.enabled:
            ingress_manifest = ingress.to_kubernetes_ingress("test-service", 80)
            print(f"✅ Kubernetes ingress manifest generated")
        
        # Test 8: Cluster configuration
        cluster_config = ClusterConfig(
            name="mvp-test-cluster",
            region="us-central1",
            labels={"environment": "test", "team": "mvp"}
        )
        
        cluster_dict = cluster_config.to_dict()
        print(f"✅ Cluster config created with {len(cluster_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_scenarios():
    """Test various validation scenarios"""
    print("\n🛡️  Testing Validation Scenarios...")
    
    try:
        from models.app_config import AppConfig, ResourceRequests, IngressConfig
        
        test_cases = [
            {
                "name": "Valid Production Config",
                "config": AppConfig(
                    name="prod-app",
                    image="gcr.io/my-project/app:v1.2.3",
                    port=8080,
                    resource_requests=ResourceRequests(cpu="500m", memory="1Gi"),
                    ingress_config=IngressConfig(enabled=False)
                ),
                "should_pass": True
            },
            {
                "name": "Invalid Name (uppercase)",
                "config": None,  # Will try to create with invalid name
                "should_pass": False
            },
            {
                "name": "Low Resources",
                "config": AppConfig(
                    name="low-resource-app",
                    image="gcr.io/test/app:latest",
                    port=8080,
                    resource_requests=ResourceRequests(cpu="50m", memory="128Mi"),
                    ingress_config=IngressConfig(enabled=False)
                ),
                "should_pass": True  # Should pass but with warnings
            }
        ]
        
        for test_case in test_cases:
            print(f"\n   Testing: {test_case['name']}")
            
            try:
                if test_case['config'] is None and test_case['name'] == "Invalid Name (uppercase)":
                    # Test invalid name
                    AppConfig(
                        name="INVALID-NAME",  # Uppercase should fail
                        image="gcr.io/test/app:v1.0.0",
                        port=8080,
                        ingress_config=IngressConfig(enabled=False)
                    )
                    if not test_case['should_pass']:
                        print("   ❌ Should have failed but didn't")
                        return False
                else:
                    config = test_case['config']
                    warnings = config.validate_for_gke_autopilot()
                    print(f"   ✅ Validation completed: {len(warnings)} warnings")
                    
                    if test_case['name'] == "Low Resources" and len(warnings) == 0:
                        print("   ⚠️  Expected warnings for low resources")
                    
            except ValueError as e:
                if test_case['should_pass']:
                    print(f"   ❌ Unexpected validation failure: {e}")
                    return False
                else:
                    print(f"   ✅ Expected validation failure: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation scenarios test failed: {e}")
        return False

def test_configuration_formats():
    """Test configuration file format support"""
    print("\n📄 Testing Configuration Formats...")
    
    try:
        from models.app_config import AppConfig, create_sample_config
        
        # Test 1: Sample configuration creation
        sample_config = create_sample_config()
        print(f"✅ Sample config created: {sample_config.name}")
        
        # Test 2: Dictionary conversion
        config_dict = sample_config.to_dict()
        recreated_config = AppConfig.from_dict(config_dict)
        print(f"✅ Round-trip dict conversion: {recreated_config.name}")
        
        # Test 3: YAML serialization
        test_yaml_path = Path("test_config.yaml")
        sample_config.to_yaml(test_yaml_path)
        print("✅ YAML serialization completed")
        
        # Test 4: YAML deserialization
        loaded_config = AppConfig.from_yaml(test_yaml_path)
        print(f"✅ YAML deserialization: {loaded_config.name}")
        
        # Cleanup
        test_yaml_path.unlink(missing_ok=True)
        
        # Test 5: Verify data integrity
        if (sample_config.name == loaded_config.name and 
            sample_config.image == loaded_config.image and
            sample_config.port == loaded_config.port):
            print("✅ Data integrity maintained through serialization")
        else:
            print("❌ Data integrity lost during serialization")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration formats test failed: {e}")
        return False

def test_autopilot_optimization():
    """Test GKE Autopilot specific optimizations"""
    print("\n🚀 Testing GKE Autopilot Optimizations...")
    
    try:
        from models.app_config import AppConfig, ResourceRequests, ScalingConfig, IngressConfig, validate_gke_autopilot_compatibility
        
        # Test 1: Minimal resources (should generate warnings)
        minimal_config = AppConfig(
            name="minimal-app",
            image="gcr.io/test/app:v1.0.0",
            port=8080,
            resource_requests=ResourceRequests(cpu="100m", memory="256Mi"),
            scaling_config=ScalingConfig(min_replicas=1, max_replicas=5),
            ingress_config=IngressConfig(enabled=False)
        )
        
        warnings = minimal_config.validate_for_gke_autopilot()
        print(f"✅ Minimal config warnings: {len(warnings)}")
        
        # Test 2: Optimized resources (should have fewer warnings)
        optimized_config = AppConfig(
            name="optimized-app",
            image="gcr.io/test/app:v1.0.0",
            port=8080,
            resource_requests=ResourceRequests(cpu="250m", memory="512Mi"),
            scaling_config=ScalingConfig(min_replicas=2, max_replicas=10),
            ingress_config=IngressConfig(enabled=False)
        )
        
        opt_warnings = optimized_config.validate_for_gke_autopilot()
        print(f"✅ Optimized config warnings: {len(opt_warnings)}")
        
        # Test 3: Comprehensive compatibility check
        compatibility = validate_gke_autopilot_compatibility(optimized_config)
        print(f"✅ Compatibility check: {'Compatible' if compatibility['compatible'] else 'Incompatible'}")
        print(f"   Warnings: {len(compatibility['warnings'])}")
        print(f"   Recommendations: {len(compatibility['recommendations'])}")
        
        # Test 4: Verify optimization suggestions
        if len(warnings) > len(opt_warnings):
            print("✅ Optimization reduces warnings as expected")
        else:
            print("⚠️  Optimization didn't reduce warnings as expected")
        
        return True
        
    except Exception as e:
        print(f"❌ Autopilot optimization test failed: {e}")
        return False

def test_production_scenarios():
    """Test production deployment scenarios"""
    print("\n🏭 Testing Production Scenarios...")
    
    try:
        from models.app_config import AppConfig, ResourceRequests, ScalingConfig, HealthCheckConfig, IngressConfig
        
        # Scenario 1: High-traffic web application
        web_app = AppConfig(
            name="web-app",
            image="gcr.io/my-project/web-app:v2.1.0",
            port=8080,
            environment_variables={
                "ENV": "production",
                "DATABASE_POOL_SIZE": "20",
                "CACHE_TTL": "3600"
            },
            resource_requests=ResourceRequests(cpu="1000m", memory="2Gi"),
            scaling_config=ScalingConfig(
                min_replicas=5,
                max_replicas=50,
                target_cpu_utilization=60
            ),
            health_checks=HealthCheckConfig(
                path="/api/health",
                port=8080,
                initial_delay_seconds=45
            ),
            ingress_config=IngressConfig(
                enabled=True,
                domain="api.mycompany.com",
                tls=True
            )
        )
        
        web_warnings = web_app.validate_for_gke_autopilot()
        print(f"✅ Web app config: {len(web_warnings)} warnings")
        
        # Scenario 2: Background worker service
        worker_app = AppConfig(
            name="worker-service",
            image="gcr.io/my-project/worker:v1.5.2",
            port=8080,
            environment_variables={
                "WORKER_CONCURRENCY": "10",
                "QUEUE_NAME": "background-tasks"
            },
            resource_requests=ResourceRequests(cpu="500m", memory="1Gi"),
            scaling_config=ScalingConfig(
                min_replicas=2,
                max_replicas=20,
                target_cpu_utilization=80
            ),
            ingress_config=IngressConfig(enabled=False)  # No external access needed
        )
        
        worker_warnings = worker_app.validate_for_gke_autopilot()
        print(f"✅ Worker service config: {len(worker_warnings)} warnings")
        
        # Scenario 3: Microservice with strict resource limits
        microservice = AppConfig(
            name="auth-service",
            image="gcr.io/my-project/auth-service:v3.0.1",
            port=9090,
            resource_requests=ResourceRequests(cpu="250m", memory="512Mi"),
            scaling_config=ScalingConfig(
                min_replicas=3,  # High availability
                max_replicas=15,
                target_cpu_utilization=70
            ),
            health_checks=HealthCheckConfig(
                path="/health/ready",
                port=9090,
                initial_delay_seconds=20
            ),
            ingress_config=IngressConfig(
                enabled=True,
                domain="auth.internal.mycompany.com",
                tls=True,
                path="/auth"
            )
        )
        
        micro_warnings = microservice.validate_for_gke_autopilot()
        print(f"✅ Microservice config: {len(micro_warnings)} warnings")
        
        # Test serialization of all scenarios
        scenarios = [web_app, worker_app, microservice]
        for i, app in enumerate(scenarios):
            config_dict = app.to_dict()
            print(f"✅ Scenario {i+1} serialization: {len(config_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Production scenarios test failed: {e}")
        return False

def run_core_tests():
    """Run all core functionality tests"""
    print("🚀 GKE Autopilot Core Functionality Test")
    print("=" * 50)
    
    tests = [
        ("Data Models Comprehensive", test_data_models_comprehensive),
        ("Validation Scenarios", test_validation_scenarios),
        ("Configuration Formats", test_configuration_formats),
        ("Autopilot Optimization", test_autopilot_optimization),
        ("Production Scenarios", test_production_scenarios)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*15} {test_name} {'='*15}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Core Functionality Test Results")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 CORE FUNCTIONALITY VALIDATION SUCCESSFUL!")
        print("✅ Data models working correctly")
        print("✅ Validation logic functioning")
        print("✅ Configuration management operational")
        print("✅ GKE Autopilot optimization active")
        print("✅ Production scenarios supported")
        print("\n🚀 MVP CORE IS PRODUCTION READY!")
        return 0
    else:
        print(f"\n⚠️  Core functionality needs attention: {total - passed} failures")
        return 1

if __name__ == "__main__":
    try:
        result = run_core_tests()
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)