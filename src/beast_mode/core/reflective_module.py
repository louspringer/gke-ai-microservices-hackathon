"""
ReflectiveModule base class for Beast Mode framework.

This module provides the foundational interface that all Beast Mode components
must implement to provide systematic health monitoring, operational visibility,
and graceful degradation capabilities.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


class ModuleStatus(Enum):
    """Status of a reflective module."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTDOWN = "shutdown"


@dataclass
class HealthIndicator:
    """Health indicator for a module component."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ReflectiveModule(ABC):
    """
    Abstract base class for all Beast Mode framework components.
    
    This class defines the interface that all Beast Mode components must implement
    to provide systematic health monitoring, operational visibility, and graceful
    degradation capabilities. It embodies the Beast Mode principle of systematic
    superiority over ad-hoc approaches.
    
    Key Principles:
    - Systematic health monitoring and reporting
    - Operational visibility and transparency
    - Graceful degradation under failure conditions
    - Self-documenting and self-validating behavior
    - PDCA methodology integration
    """
    
    def __init__(self):
        """Initialize the reflective module."""
        self._module_id = f"{self.__class__.__name__}_{id(self)}"
        self._initialization_time = datetime.utcnow()
    
    @abstractmethod
    def get_module_status(self) -> ModuleStatus:
        """
        Get the current operational status of the module.
        
        This method must return the current status of the module, indicating
        whether it's healthy, degraded, or experiencing issues.
        
        Returns:
            ModuleStatus: Current status of the module
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the module is currently healthy.
        
        This is a convenience method that should return True if the module
        is operating normally, False otherwise.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_health_indicators(self) -> List[HealthIndicator]:
        """
        Get detailed health indicators for the module.
        
        This method should return a list of health indicators that provide
        detailed information about the module's operational state, including
        any sub-components or dependencies.
        
        Returns:
            List[HealthIndicator]: List of health indicators
        """
        pass
    
    @abstractmethod
    def get_operational_info(self) -> Dict[str, Any]:
        """
        Get operational information about the module.
        
        This method should return comprehensive operational information
        including configuration, metrics, capabilities, and current state.
        
        Returns:
            Dict[str, Any]: Operational information dictionary
        """
        pass
    
    def get_documentation_compliance(self) -> Dict[str, Any]:
        """
        Get documentation compliance information.
        
        This method provides information about the module's documentation
        compliance, including docstring coverage, type hints, and examples.
        
        Returns:
            Dict[str, Any]: Documentation compliance information
        """
        return {
            'module_name': self.__class__.__name__,
            'has_docstrings': bool(self.__class__.__doc__),
            'has_type_hints': True,  # Assumed for Python 3.9+
            'documentation_coverage': 85,  # Default estimate
            'last_updated': self._initialization_time.isoformat(),
        }
    
    def graceful_degradation_info(self) -> Dict[str, Any]:
        """
        Get information about graceful degradation capabilities.
        
        This method provides information about how the module handles
        degraded conditions and what capabilities remain available.
        
        Returns:
            Dict[str, Any]: Graceful degradation information
        """
        return {
            'supports_degradation': True,
            'degradation_triggers': [
                'Dependency failures',
                'Resource constraints',
                'Configuration errors'
            ],
            'degraded_capabilities': [
                'Limited functionality',
                'Reduced performance',
                'Basic operations only'
            ],
            'recovery_procedures': [
                'Automatic retry mechanisms',
                'Fallback to safe defaults',
                'Manual intervention options'
            ]
        }
    
    def get_module_id(self) -> str:
        """Get the unique module identifier."""
        return self._module_id
    
    def get_initialization_time(self) -> datetime:
        """Get the module initialization timestamp."""
        return self._initialization_time
    
    def get_uptime(self) -> float:
        """
        Get the module uptime in seconds.
        
        Returns:
            float: Uptime in seconds since initialization
        """
        return (datetime.utcnow() - self._initialization_time).total_seconds()
    
    def validate_interface_compliance(self) -> Dict[str, Any]:
        """
        Validate that the module properly implements the ReflectiveModule interface.
        
        This method performs self-validation to ensure the module correctly
        implements all required methods and behaviors.
        
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'interface_compliance': True,
            'missing_methods': [],
            'validation_errors': [],
            'validation_timestamp': datetime.utcnow().isoformat()
        }
        
        # Check required methods
        required_methods = [
            'get_module_status',
            'is_healthy', 
            'get_health_indicators',
            'get_operational_info'
        ]
        
        for method_name in required_methods:
            if not hasattr(self, method_name):
                validation_results['missing_methods'].append(method_name)
                validation_results['interface_compliance'] = False
            elif not callable(getattr(self, method_name)):
                validation_results['validation_errors'].append(
                    f"{method_name} is not callable"
                )
                validation_results['interface_compliance'] = False
        
        # Test method calls
        try:
            status = self.get_module_status()
            if not isinstance(status, ModuleStatus):
                validation_results['validation_errors'].append(
                    "get_module_status() must return ModuleStatus enum"
                )
                validation_results['interface_compliance'] = False
        except Exception as e:
            validation_results['validation_errors'].append(
                f"get_module_status() failed: {str(e)}"
            )
            validation_results['interface_compliance'] = False
        
        try:
            healthy = self.is_healthy()
            if not isinstance(healthy, bool):
                validation_results['validation_errors'].append(
                    "is_healthy() must return boolean"
                )
                validation_results['interface_compliance'] = False
        except Exception as e:
            validation_results['validation_errors'].append(
                f"is_healthy() failed: {str(e)}"
            )
            validation_results['interface_compliance'] = False
        
        try:
            indicators = self.get_health_indicators()
            if not isinstance(indicators, list):
                validation_results['validation_errors'].append(
                    "get_health_indicators() must return list"
                )
                validation_results['interface_compliance'] = False
            elif indicators and not all(isinstance(ind, HealthIndicator) for ind in indicators):
                validation_results['validation_errors'].append(
                    "get_health_indicators() must return list of HealthIndicator objects"
                )
                validation_results['interface_compliance'] = False
        except Exception as e:
            validation_results['validation_errors'].append(
                f"get_health_indicators() failed: {str(e)}"
            )
            validation_results['interface_compliance'] = False
        
        try:
            info = self.get_operational_info()
            if not isinstance(info, dict):
                validation_results['validation_errors'].append(
                    "get_operational_info() must return dictionary"
                )
                validation_results['interface_compliance'] = False
        except Exception as e:
            validation_results['validation_errors'].append(
                f"get_operational_info() failed: {str(e)}"
            )
            validation_results['interface_compliance'] = False
        
        return validation_results
    
    def __str__(self) -> str:
        """String representation of the module."""
        return f"{self.__class__.__name__}(id={self._module_id}, status={self.get_module_status().value})"
    
    def __repr__(self) -> str:
        """Detailed representation of the module."""
        return (f"{self.__class__.__name__}("
                f"id={self._module_id}, "
                f"status={self.get_module_status().value}, "
                f"healthy={self.is_healthy()}, "
                f"uptime={self.get_uptime():.1f}s)")


class ReflectiveModuleRegistry:
    """
    Registry for managing ReflectiveModule instances.
    
    This class provides a centralized registry for all ReflectiveModule
    instances in the system, enabling system-wide health monitoring
    and operational visibility.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._modules: Dict[str, ReflectiveModule] = {}
        self._creation_time = datetime.utcnow()
    
    def register_module(self, module: ReflectiveModule, 
                       module_id: Optional[str] = None) -> str:
        """
        Register a module with the registry.
        
        Args:
            module: The module to register
            module_id: Optional custom module ID
            
        Returns:
            str: The assigned module ID
        """
        if module_id is None:
            module_id = module.get_module_id()
        
        self._modules[module_id] = module
        return module_id
    
    def unregister_module(self, module_id: str) -> bool:
        """
        Unregister a module from the registry.
        
        Args:
            module_id: ID of the module to unregister
            
        Returns:
            bool: True if module was found and removed
        """
        return self._modules.pop(module_id, None) is not None
    
    def get_module(self, module_id: str) -> Optional[ReflectiveModule]:
        """
        Get a module by ID.
        
        Args:
            module_id: ID of the module to retrieve
            
        Returns:
            Optional[ReflectiveModule]: The module if found
        """
        return self._modules.get(module_id)
    
    def list_modules(self) -> List[str]:
        """
        List all registered module IDs.
        
        Returns:
            List[str]: List of module IDs
        """
        return list(self._modules.keys())
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get system-wide health information.
        
        Returns:
            Dict[str, Any]: System health information
        """
        total_modules = len(self._modules)
        healthy_modules = sum(1 for module in self._modules.values() if module.is_healthy())
        
        health_by_status = {}
        for module in self._modules.values():
            status = module.get_module_status().value
            health_by_status[status] = health_by_status.get(status, 0) + 1
        
        return {
            'total_modules': total_modules,
            'healthy_modules': healthy_modules,
            'unhealthy_modules': total_modules - healthy_modules,
            'health_percentage': (healthy_modules / total_modules * 100) if total_modules > 0 else 0,
            'status_breakdown': health_by_status,
            'registry_uptime': (datetime.utcnow() - self._creation_time).total_seconds(),
            'last_check': datetime.utcnow().isoformat()
        }
    
    def get_all_health_indicators(self) -> Dict[str, List[HealthIndicator]]:
        """
        Get health indicators from all registered modules.
        
        Returns:
            Dict[str, List[HealthIndicator]]: Health indicators by module ID
        """
        indicators = {}
        for module_id, module in self._modules.items():
            try:
                indicators[module_id] = module.get_health_indicators()
            except Exception as e:
                indicators[module_id] = [HealthIndicator(
                    name="health_check_error",
                    status="unhealthy",
                    message=f"Failed to get health indicators: {str(e)}"
                )]
        
        return indicators


# Global registry instance
_global_registry = ReflectiveModuleRegistry()


def get_global_registry() -> ReflectiveModuleRegistry:
    """Get the global ReflectiveModule registry."""
    return _global_registry