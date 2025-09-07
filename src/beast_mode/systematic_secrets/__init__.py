"""
Systematic Secrets Management - Beast Mode Framework

A comprehensive, systematic approach to secrets management that integrates
with the Beast Mode framework's ReflectiveModule pattern and PDCA methodology.

This module provides:
- Environment-isolated secret storage and management
- Automatic secret rotation with configurable policies
- Multi-backend support (local, Vault, AWS Secrets Manager)
- Comprehensive audit logging and compliance reporting
- Integration with CI/CD pipelines and development workflows
"""

from .core.secrets_manager import SecretsManager
from .models.secret import Secret, SecretMetadata
from .models.access_context import AccessContext, Principal, AccessPolicy
from .models.rotation_policy import RotationPolicy, RotationStrategy
from .models.environment import Environment, EnvironmentConfig
from .backends.base import SecretBackend
from .backends.local_adapter import LocalAdapter
__version__ = "0.1.0"
__all__ = [
    "SecretsManager",
    "Secret",
    "SecretMetadata",
    "AccessContext",
    "Principal",
    "AccessPolicy",
    "RotationPolicy",
    "RotationStrategy",
    "Environment",
    "EnvironmentConfig",
    "SecretBackend",
    "LocalAdapter",
    "LocalAdapter",
]