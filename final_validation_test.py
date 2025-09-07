#!/usr/bin/env python3
"""
Final Validation Test - Complete Repository Health Check
Tests all components including newly copied GKE files
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description, allow_failure=False):
    """Run a command and report results"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {description} - PASSED")
            return True
        else:
            if allow_failure:
                print(f"  ⚠️  {description} - SKIPPED (expected)")
                return True
            else:
                print(f"  ❌ {description} - FAILED")
                print(f"     Error: {result.stderr.strip()}")
                return False
    except Exception as e:
        print(f"  ❌ {description} - ERROR: {e}")
        return False

def check_file_exists(file_path, description):
    """Check if a file exists"""
    if Path(file_path).exists():
        print(f"  ✅ {description} - EXISTS")
        return True
    else:
        print(f"  ❌ {description} - MISSING")
        return False

def main():
    print("🧬 Final Beast Mode Repository Validation")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    # Core Python tests
    tests = [
        ("python3 -m py_compile repo_health_check.py", "Python syntax validation"),
        ("python3 -c 'import gke_local.config.manager'", "Core config import"),
        ("python3 -c 'import gke_local.cluster.kind_manager'", "Cluster manager import"),
        ("python3 -c 'import gke_local.cli.base'", "CLI base import"),
        ("python3 -m pytest tests/test_basic.py -v", "Basic functionality tests"),
        ("python3 -m pytest tests/test_config.py -v", "Configuration tests"),
        ("python3 -m pytest tests/test_cluster.py -v", "Cluster management tests"),
    ]
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    # Script syntax validation
    script_tests = [
        ("bash -n deployment/autopilot/deploy.sh", "Autopilot deployment script"),
        ("bash -n deployment/gke/deploy-gke.sh", "GKE deployment script"),
        ("bash -n deployment/gke/deploy-app-only.sh", "GKE app deployment script"),
        ("bash -n deployment/gke/helm-deploy.sh", "Helm deployment script"),
        ("bash -n scripts/validate-deployment.sh", "Validation script"),
        ("bash -n scripts/cost-monitor.sh", "Cost monitor script"),
        ("bash -n scripts/spawn-gke-hackathon.sh", "GKE hackathon spawn script"),
        ("bash -n scripts/deploy-spawn.sh", "Deploy spawn script"),
        ("bash -n scripts/deploy-container.sh", "Container deploy script"),
    ]
    
    for cmd, description in script_tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    # File existence checks
    file_checks = [
        ("README.md", "Main README"),
        ("pyproject.toml", "Python project config"),
        (".kiro/BEAST_MODE_DNA.md", "Beast Mode DNA"),
        ("deployment/DEPLOYMENT_OPTIONS.md", "Deployment options doc"),
        ("deployment/SEPARATION_OF_CONCERNS.md", "Separation of concerns doc"),
        ("deployment/gke/kubernetes-manifests.yaml", "Kubernetes manifests"),
        ("deployment/gke/helm-chart", "Helm chart directory"),
        ("examples/sample-app", "Sample app directory"),
        ("docs", "Documentation directory"),
        ("src/__init__.py", "Source package init"),
        ("gke_local/__init__.py", "GKE local package init"),
    ]
    
    for file_path, description in file_checks:
        if check_file_exists(file_path, description):
            passed += 1
        else:
            failed += 1
    
    # Directory structure validation
    structure_tests = [
        ("ls -la deployment/", "Deployment directory structure"),
        ("ls -la deployment/gke/", "GKE deployment structure"),
        ("ls -la deployment/gcp/", "GCP deployment structure"),
        ("ls -la examples/", "Examples directory structure"),
        ("ls -la docs/", "Documentation structure"),
        ("ls -la gke_local/", "GKE local module structure"),
        ("ls -la .kiro/", "Kiro configuration structure"),
    ]
    
    for cmd, description in structure_tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    # Executable permissions check
    executable_checks = [
        ("test -x deployment/autopilot/deploy.sh", "Autopilot deploy script executable"),
        ("test -x deployment/gke/deploy-gke.sh", "GKE deploy script executable"),
        ("test -x deployment/gke/deploy-app-only.sh", "GKE app deploy script executable"),
        ("test -x deployment/gke/helm-deploy.sh", "Helm deploy script executable"),
        ("test -x scripts/validate-deployment.sh", "Validation script executable"),
        ("test -x scripts/cost-monitor.sh", "Cost monitor script executable"),
        ("test -x scripts/spawn-gke-hackathon.sh", "GKE spawn script executable"),
        ("test -x scripts/deploy-spawn.sh", "Deploy spawn script executable"),
        ("test -x scripts/deploy-container.sh", "Container deploy script executable"),
    ]
    
    for cmd, description in executable_checks:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Final Validation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 REPOSITORY FULLY VALIDATED!")
        print("🧬 Beast Mode DNA is complete and ready for systematic excellence!")
        print("🚀 All GKE Autopilot files successfully integrated!")
        print("⚡ Ready for hackathon deployment and production use!")
        return 0
    else:
        print(f"⚠️  {failed} validation checks failed. Repository needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())