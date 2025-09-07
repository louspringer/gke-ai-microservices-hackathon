#!/usr/bin/env python3
"""
Comprehensive Repository Test Suite
Tests all major components and functionality
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {description} - PASSED")
            return True
        else:
            print(f"  ❌ {description} - FAILED")
            print(f"     Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  ❌ {description} - ERROR: {e}")
        return False

def main():
    print("🧬 Beast Mode Repository Comprehensive Test Suite")
    print("=" * 50)
    
    tests = [
        # Python syntax and imports
        ("python3 -m py_compile repo_health_check.py", "Python syntax validation"),
        ("python3 -c 'import gke_local.config.manager'", "Core config import"),
        ("python3 -c 'import gke_local.cluster.kind_manager'", "Cluster manager import"),
        ("python3 -c 'import gke_local.cli.base'", "CLI base import"),
        
        # Test suite execution
        ("python3 -m pytest tests/test_basic.py -v", "Basic functionality tests"),
        ("python3 -m pytest tests/test_config.py -v", "Configuration tests"),
        ("python3 -m pytest tests/test_cluster.py -v", "Cluster management tests"),
        
        # Script validation
        ("bash -n deployment/autopilot/deploy.sh", "Deployment script syntax"),
        ("bash -n scripts/validate-deployment.sh", "Validation script syntax"),
        ("bash -n scripts/cost-monitor.sh", "Cost monitor script syntax"),
        
        # Project structure validation
        ("ls -la src/", "Source directory structure"),
        ("ls -la gke_local/", "GKE local module structure"),
        ("ls -la .kiro/", "Kiro configuration structure"),
        ("ls -la deployment/autopilot/", "Deployment structure"),
        
        # Documentation validation
        ("head -20 README.md", "README content check"),
        ("head -10 .kiro/BEAST_MODE_DNA.md", "Beast Mode DNA check"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Repository is healthy and ready for Beast Mode.")
        return 0
    else:
        print(f"⚠️  {failed} tests failed. Repository needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())