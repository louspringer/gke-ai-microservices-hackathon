#!/usr/bin/env python3
"""
Quick test script for GKE Autopilot deployment framework
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.app_config import AppConfig, ResourceRequests, ScalingConfig, HealthCheckConfig, IngressConfig
from core.validation_engine import ValidationEngine
from core.template_engine import TemplateEngine, TemplateContext


async def test_validation():
    """Test validation engine"""
    print("🔍 Testing validation engine...")
    
    # Create test app config
    app_config = AppConfig(
        name="test-app",
        image="gcr.io/google-samples/hello-app:1.0",
        port=8080,
        resource_requests=ResourceRequests(cpu="250m", memory="512Mi"),
        scaling_config=ScalingConfig(min_replicas=2, max_replicas=10),
        health_checks=HealthCheckConfig(path="/health", port=8080),
        ingress_config=IngressConfig(enabled=True, domain="test-app.example.com", tls=True)
    )
    
    # Validate configuration
    async with ValidationEngine() as validator:
        report = await validator.validate_app_config(app_config)
        
        print(f"✅ Validation completed: {'VALID' if report.valid else 'INVALID'}")
        print(f"   Errors: {len(report.get_errors())}")
        print(f"   Warnings: {len(report.get_warnings())}")
        print(f"   Recommendations: {len(report.get_recommendations())}")
        
        if report.get_warnings():
            print("\n⚠️  Warnings:")
            for warning in report.get_warnings():
                print(f"   • {warning.message}")
        
        if report.get_recommendations():
            print("\n💡 Recommendations:")
            for rec in report.get_recommendations():
                print(f"   • {rec.message}")


def test_template_generation():
    """Test template engine"""
    print("\n🎨 Testing template engine...")
    
    # Create test app config
    app_config = AppConfig(
        name="test-app",
        image="gcr.io/google-samples/hello-app:1.0",
        port=8080,
        environment_variables={"ENV": "test", "LOG_LEVEL": "info"},
        resource_requests=ResourceRequests(cpu="250m", memory="512Mi"),
        scaling_config=ScalingConfig(min_replicas=2, max_replicas=10),
        health_checks=HealthCheckConfig(path="/health", port=8080),
        ingress_config=IngressConfig(enabled=True, domain="test-app.example.com", tls=True)
    )
    
    # Generate manifests
    template_engine = TemplateEngine()
    context = TemplateContext(
        app_config=app_config,
        project_id="test-project",
        namespace="default",
        environment="test"
    )
    
    manifests = template_engine.generate_manifests(context)
    
    print(f"✅ Generated {len(manifests)} Kubernetes manifests:")
    for manifest in manifests:
        kind = manifest.get('kind', 'Unknown')
        name = manifest.get('metadata', {}).get('name', 'unnamed')
        print(f"   • {kind}: {name}")
    
    # Validate manifests
    total_warnings = 0
    for manifest in manifests:
        warnings = template_engine.validate_manifest(manifest)
        total_warnings += len(warnings)
        if warnings:
            print(f"   ⚠️  {manifest.get('kind')} has {len(warnings)} warnings")
    
    print(f"   Total validation warnings: {total_warnings}")


def test_configuration_management():
    """Test configuration management"""
    print("\n⚙️  Testing configuration management...")
    
    from config.configuration_manager import ConfigurationManager
    
    config_manager = ConfigurationManager()
    
    # Create sample configurations
    config_manager.create_sample_configs()
    print("✅ Sample configurations created")
    
    # Test configuration loading
    sample_path = config_manager.config_dir / "samples" / "app-config.yaml"
    if sample_path.exists():
        config_data = config_manager.load_configuration(sample_path)
        app_config = config_manager.create_app_config(config_data)
        print(f"✅ Loaded sample config: {app_config.name}")
        
        # Test GKE Autopilot validation
        validation_result = config_manager.validate_gke_autopilot_config(config_data)
        print(f"   Autopilot compatible: {'Yes' if validation_result['valid'] else 'No'}")
        if validation_result['warnings']:
            print(f"   Warnings: {len(validation_result['warnings'])}")
    else:
        print("❌ Sample configuration not found")


async def main():
    """Run all tests"""
    print("🚀 GKE Autopilot Framework Test Suite")
    print("=" * 50)
    
    try:
        # Test validation engine
        await test_validation()
        
        # Test template generation
        test_template_generation()
        
        # Test configuration management
        test_configuration_management()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())