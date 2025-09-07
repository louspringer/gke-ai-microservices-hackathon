#!/usr/bin/env python3
"""
Simple validation test for GKE Autopilot framework components
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing module imports...")
    
    try:
        # Test data models
        from models.app_config import AppConfig, ResourceRequests, ScalingConfig
        print("✅ Data models imported successfully")
        
        # Test basic app config creation
        from models.app_config import IngressConfig
        
        app_config = AppConfig(
            name="test-app",
            image="gcr.io/google-samples/hello-app:1.0",
            port=8080,
            ingress_config=IngressConfig(enabled=False)  # Disable ingress for simple test
        )
        print(f"✅ Created app config: {app_config.name}")
        
        # Test resource validation
        resources = ResourceRequests(cpu="250m", memory="512Mi")
        print(f"✅ Created resource config: {resources.cpu}, {resources.memory}")
        
        # Test configuration serialization
        config_dict = app_config.to_dict()
        print(f"✅ Serialized config with {len(config_dict)} fields")
        
        # Test GKE Autopilot validation
        warnings = app_config.validate_for_gke_autopilot()
        print(f"✅ GKE Autopilot validation: {len(warnings)} warnings")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_engine():
    """Test template engine functionality"""
    print("\n🎨 Testing template engine...")
    
    try:
        from core.template_engine import TemplateEngine
        
        engine = TemplateEngine()
        templates = engine.get_available_templates()
        print(f"✅ Template engine initialized with {len(templates)} templates")
        print(f"   Available templates: {', '.join(templates)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template engine test failed: {e}")
        return False

def test_configuration_manager():
    """Test configuration manager"""
    print("\n⚙️  Testing configuration manager...")
    
    try:
        from config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager("test_config")
        print("✅ Configuration manager initialized")
        
        # Test sample config creation
        config_manager.create_sample_configs()
        print("✅ Sample configurations created")
        
        # Check if files were created
        sample_dir = Path("test_config/samples")
        if sample_dir.exists():
            files = list(sample_dir.glob("*.yaml"))
            print(f"✅ Created {len(files)} sample files")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration manager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 GKE Autopilot Framework - Simple Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Run tests
    if test_imports():
        tests_passed += 1
    
    if test_template_engine():
        tests_passed += 1
    
    if test_configuration_manager():
        tests_passed += 1
    
    # Summary
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Framework is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())