"""Validation utilities for GKE Local."""

import re
from typing import List, Optional
from pathlib import Path


def validate_project_name(name: str) -> bool:
    """Validate project name format.
    
    Args:
        name: Project name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    
    # Must be alphanumeric with hyphens or underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name))


def validate_kubernetes_version(version: str) -> bool:
    """Validate Kubernetes version format.
    
    Args:
        version: Version string to validate (e.g., "1.28")
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^\d+\.\d+$'
    return bool(re.match(pattern, version))


def validate_port(port: int) -> bool:
    """Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 1 <= port <= 65535


def validate_paths(paths: List[str]) -> List[str]:
    """Validate and filter existing paths.
    
    Args:
        paths: List of paths to validate
        
    Returns:
        List of valid existing paths
    """
    valid_paths = []
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            valid_paths.append(path_str)
    
    return valid_paths


def validate_timeout(timeout_str: str) -> bool:
    """Validate timeout string format (e.g., "30s", "5m").
    
    Args:
        timeout_str: Timeout string to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^\d+[smh]$'
    return bool(re.match(pattern, timeout_str))


def get_validation_errors(config_dict: dict) -> List[str]:
    """Get list of validation errors for configuration.
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Validate project name
    project_name = config_dict.get('project_name')
    if not project_name or not validate_project_name(project_name):
        errors.append("Invalid project name: must be alphanumeric with hyphens or underscores")
    
    # Validate cluster configuration
    cluster = config_dict.get('cluster', {})
    k8s_version = cluster.get('kubernetes_version')
    if k8s_version and not validate_kubernetes_version(k8s_version):
        errors.append("Invalid Kubernetes version: must be in format 'X.Y'")
    
    nodes = cluster.get('nodes')
    if nodes is not None and (not isinstance(nodes, int) or nodes < 1):
        errors.append("Cluster nodes must be a positive integer")
    
    # Validate ports
    ports_to_check = [
        ('cluster.registry_port', cluster.get('registry_port')),
        ('cluster.ingress_port', cluster.get('ingress_port')),
        ('cluster.api_server_port', cluster.get('api_server_port')),
    ]
    
    for port_name, port_value in ports_to_check:
        if port_value is not None and not validate_port(port_value):
            errors.append(f"Invalid {port_name}: must be between 1 and 65535")
    
    # Validate timeout strings
    simulation = config_dict.get('simulation', {})
    cloud_run = simulation.get('cloud_run', {})
    
    cold_start_delay = cloud_run.get('cold_start_delay')
    if cold_start_delay and not validate_timeout(cold_start_delay):
        errors.append("Invalid cold_start_delay: must be in format like '2s', '30s', '5m'")
    
    timeout = cloud_run.get('timeout')
    if timeout and not validate_timeout(timeout):
        errors.append("Invalid timeout: must be in format like '300s', '5m', '1h'")
    
    return errors