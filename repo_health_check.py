#!/usr/bin/env python3
"""
Repository Health Check - Identify corruption and missing files
"""

import os
import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class RepoHealthChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def check_python_syntax(self) -> Dict[str, List[str]]:
        """Check all Python files for syntax errors"""
        syntax_errors = []
        
        for py_file in Path('.').rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(f"{py_file}: {e}")
            except UnicodeDecodeError as e:
                syntax_errors.append(f"{py_file}: Unicode decode error - {e}")
            except Exception as e:
                syntax_errors.append(f"{py_file}: {e}")
                
        return {"syntax_errors": syntax_errors}
    
    def check_required_files(self) -> Dict[str, List[str]]:
        """Check for required project files"""
        required_files = [
            'README.md',
            'pyproject.toml',
            'requirements.txt',
            '.gitignore',
            'src/__init__.py',
            'tests/__init__.py',
            'deployment/autopilot/deploy.sh',
            'scripts/validate-deployment.sh',
            '.kiro/BEAST_MODE_DNA.md'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
                
        return {"missing_files": missing_files}
    
    def check_import_integrity(self) -> Dict[str, List[str]]:
        """Check for broken imports"""
        import_errors = []
        
        # Test key imports
        test_imports = [
            'gke_local.config.manager',
            'gke_local.cluster.kind_manager',
            'gke_local.cli.base'
        ]
        
        for module in test_imports:
            try:
                __import__(module)
            except ImportError as e:
                import_errors.append(f"Cannot import {module}: {e}")
            except Exception as e:
                import_errors.append(f"Error importing {module}: {e}")
                
        return {"import_errors": import_errors}
    
    def check_executable_permissions(self) -> Dict[str, List[str]]:
        """Check shell scripts have executable permissions"""
        script_files = []
        for script in Path('.').rglob('*.sh'):
            if not os.access(script, os.X_OK):
                script_files.append(str(script))
                
        return {"non_executable_scripts": script_files}
    
    def check_git_integrity(self) -> Dict[str, List[str]]:
        """Check git repository integrity"""
        git_issues = []
        
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                git_issues.append("Git repository appears corrupted")
        except FileNotFoundError:
            git_issues.append("Git not found")
        except Exception as e:
            git_issues.append(f"Git check failed: {e}")
            
        return {"git_issues": git_issues}
    
    def run_full_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        
        print("🔍 Running repository health check...")
        
        print("  Checking Python syntax...")
        results.update(self.check_python_syntax())
        
        print("  Checking required files...")
        results.update(self.check_required_files())
        
        print("  Checking import integrity...")
        results.update(self.check_import_integrity())
        
        print("  Checking executable permissions...")
        results.update(self.check_executable_permissions())
        
        print("  Checking git integrity...")
        results.update(self.check_git_integrity())
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive health report"""
        report = []
        report.append("# Repository Health Check Report")
        report.append("=" * 50)
        
        total_issues = 0
        
        for check_name, issues in results.items():
            if issues:
                total_issues += len(issues)
                report.append(f"\n## {check_name.replace('_', ' ').title()}")
                report.append(f"Found {len(issues)} issues:")
                for issue in issues:
                    report.append(f"  ❌ {issue}")
            else:
                report.append(f"\n## {check_name.replace('_', ' ').title()}")
                report.append("  ✅ No issues found")
        
        report.append(f"\n## Summary")
        if total_issues == 0:
            report.append("🎉 Repository is healthy!")
        else:
            report.append(f"⚠️  Found {total_issues} total issues that need attention")
            
        return "\n".join(report)

if __name__ == "__main__":
    checker = RepoHealthChecker()
    results = checker.run_full_check()
    report = checker.generate_report(results)
    
    print("\n" + report)
    
    # Exit with error code if issues found
    total_issues = sum(len(issues) for issues in results.values())
    sys.exit(1 if total_issues > 0 else 0)