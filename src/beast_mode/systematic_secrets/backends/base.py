"""Base interface for secret storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.secret import Secret
from ..models.environment import Environment


class SecretBackend(ABC):
    """
    Abstract base class for secret storage backends.
    
    This interface defines the contract that all secret storage backends
    must implement to provide consistent secret management capabilities
    across different storage systems (local, Vault, AWS Secrets Manager, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the backend with configuration.
        
        Args:
            config: Backend-specific configuration dictionary
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the backend connection and resources.
        
        This method should establish connections, validate configuration,
        and prepare the backend for use.
        
        Raises:
            BackendError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the backend.
        
        Returns:
            Dictionary containing health status and metrics
            
        Example:
            {
                'status': 'healthy',
                'response_time_ms': 45,
                'last_check': '2023-01-01T12:00:00Z',
                'details': {...}
            }
        """
        pass
    
    @abstractmethod
    async def store_secret(self, secret: Secret, environment: Environment) -> bool:
        """
        Store a secret in the backend.
        
        Args:
            secret: The secret to store
            environment: The environment context
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If storage fails
            ValidationError: If secret validation fails
        """
        pass
    
    @abstractmethod
    async def retrieve_secret(self, secret_id: str, environment: Environment) -> Optional[Secret]:
        """
        Retrieve a secret from the backend.
        
        Args:
            secret_id: The ID of the secret to retrieve
            environment: The environment context
            
        Returns:
            The secret if found, None otherwise
            
        Raises:
            BackendError: If retrieval fails
            AccessDeniedError: If access is not allowed
        """
        pass
    
    @abstractmethod
    async def update_secret(self, secret: Secret, environment: Environment) -> bool:
        """
        Update an existing secret in the backend.
        
        Args:
            secret: The updated secret
            environment: The environment context
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If update fails
            NotFoundError: If secret doesn't exist
        """
        pass
    
    @abstractmethod
    async def delete_secret(self, secret_id: str, environment: Environment) -> bool:
        """
        Delete a secret from the backend.
        
        Args:
            secret_id: The ID of the secret to delete
            environment: The environment context
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If deletion fails
            NotFoundError: If secret doesn't exist
        """
        pass
    
    @abstractmethod
    async def list_secrets(self, environment: Environment, 
                          filters: Optional[Dict[str, Any]] = None) -> List[Secret]:
        """
        List secrets in the backend for an environment.
        
        Args:
            environment: The environment context
            filters: Optional filters to apply (name pattern, type, etc.)
            
        Returns:
            List of secrets matching the criteria
            
        Raises:
            BackendError: If listing fails
        """
        pass
    
    @abstractmethod
    async def rotate_secret(self, secret_id: str, new_value: str, 
                           environment: Environment) -> bool:
        """
        Rotate a secret to a new value.
        
        Args:
            secret_id: The ID of the secret to rotate
            new_value: The new secret value
            environment: The environment context
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If rotation fails
            NotFoundError: If secret doesn't exist
        """
        pass
    
    @abstractmethod
    async def get_secret_versions(self, secret_id: str, 
                                 environment: Environment) -> List[Dict[str, Any]]:
        """
        Get version history for a secret.
        
        Args:
            secret_id: The ID of the secret
            environment: The environment context
            
        Returns:
            List of version information dictionaries
            
        Raises:
            BackendError: If retrieval fails
            NotFoundError: If secret doesn't exist
        """
        pass
    
    @abstractmethod
    async def backup_secrets(self, environment: Environment, 
                            backup_path: str) -> bool:
        """
        Create a backup of secrets for an environment.
        
        Args:
            environment: The environment to backup
            backup_path: Path or identifier for the backup
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If backup fails
        """
        pass
    
    @abstractmethod
    async def restore_secrets(self, environment: Environment, 
                             backup_path: str) -> bool:
        """
        Restore secrets from a backup.
        
        Args:
            environment: The environment to restore to
            backup_path: Path or identifier of the backup
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BackendError: If restore fails
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up backend resources.
        
        This method should close connections and release resources.
        Default implementation does nothing.
        """
        pass
    
    def is_initialized(self) -> bool:
        """Check if the backend is initialized."""
        return self._initialized
    
    def get_backend_type(self) -> str:
        """Get the backend type identifier."""
        return self.__class__.__name__
    
    def get_config(self) -> Dict[str, Any]:
        """Get the backend configuration (without sensitive data)."""
        # Return a copy without sensitive keys
        sensitive_keys = {'password', 'token', 'secret', 'key', 'credential'}
        return {
            k: v for k, v in self.config.items() 
            if not any(sensitive in k.lower() for sensitive in sensitive_keys)
        }


class BackendError(Exception):
    """Base exception for backend errors."""
    
    def __init__(self, message: str, backend_type: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.backend_type = backend_type
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class ValidationError(BackendError):
    """Exception for validation errors."""
    pass


class AccessDeniedError(BackendError):
    """Exception for access denied errors."""
    pass


class NotFoundError(BackendError):
    """Exception for not found errors."""
    pass


class ConnectionError(BackendError):
    """Exception for connection errors."""
    pass