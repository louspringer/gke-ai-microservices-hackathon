"""Local file-based secret storage adapter."""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import base64
import hashlib

from .base import SecretBackend, BackendError, ValidationError, NotFoundError
from ..models.secret import Secret
from ..models.environment import Environment


class LocalAdapter(SecretBackend):
    """
    Local file-based secret storage adapter with encryption.
    
    This adapter stores secrets in encrypted files on the local filesystem,
    providing a secure storage option for development and testing environments.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the local adapter.
        
        Args:
            config: Configuration dictionary with keys:
                - storage_path: Path to store encrypted files
                - master_key: Master key for encryption (optional, will generate if not provided)
                - backup_enabled: Whether to enable automatic backups
                - backup_retention_days: How long to keep backups
        """
        super().__init__(config)
        self.storage_path = Path(config.get('storage_path', './secrets'))
        self.backup_enabled = config.get('backup_enabled', True)
        self.backup_retention_days = config.get('backup_retention_days', 30)
        self._cipher_suite = None
        self._master_key = config.get('master_key')
    
    async def initialize(self) -> None:
        """Initialize the local storage."""
        try:
            # Create storage directory
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize encryption
            await self._initialize_encryption()
            
            # Create environment directories
            for env_name in ['development', 'staging', 'production', 'test']:
                env_path = self.storage_path / env_name
                env_path.mkdir(exist_ok=True)
            
            self._initialized = True
            
        except Exception as e:
            raise BackendError(f"Failed to initialize local adapter: {str(e)}", "LocalAdapter")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on local storage."""
        start_time = datetime.utcnow()
        
        try:
            # Check if storage path is accessible
            if not self.storage_path.exists():
                return {
                    'status': 'unhealthy',
                    'error': 'Storage path does not exist',
                    'response_time_ms': 0,
                    'last_check': start_time.isoformat()
                }
            
            # Check write permissions
            test_file = self.storage_path / '.health_check'
            test_file.write_text('test')
            test_file.unlink()
            
            # Check encryption
            if not self._cipher_suite:
                return {
                    'status': 'unhealthy',
                    'error': 'Encryption not initialized',
                    'response_time_ms': 0,
                    'last_check': start_time.isoformat()
                }
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'last_check': end_time.isoformat(),
                'details': {
                    'storage_path': str(self.storage_path),
                    'writable': True,
                    'encryption_enabled': True
                }
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': response_time,
                'last_check': end_time.isoformat()
            }
    
    async def store_secret(self, secret: Secret, environment: Environment) -> bool:
        """Store a secret in encrypted local file."""
        try:
            env_path = self.storage_path / environment.name
            env_path.mkdir(exist_ok=True)
            
            secret_file = env_path / f"{secret.id}.json"
            
            # Encrypt the secret data using Pydantic's JSON serialization
            secret_json = secret.model_dump_json()
            encrypted_data = self._encrypt_data(secret_json)
            
            # Write encrypted data to file
            with open(secret_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Create backup if enabled
            if self.backup_enabled:
                await self._create_backup(secret, environment)
            
            return True
            
        except Exception as e:
            raise BackendError(f"Failed to store secret: {str(e)}", "LocalAdapter")
    
    async def retrieve_secret(self, secret_id: str, environment: Environment) -> Optional[Secret]:
        """Retrieve a secret from encrypted local file."""
        try:
            secret_file = self.storage_path / environment.name / f"{secret_id}.json"
            
            if not secret_file.exists():
                return None
            
            # Read and decrypt the file
            with open(secret_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            
            # Parse using Pydantic
            secret = Secret.model_validate_json(decrypted_data)
            secret.metadata.update_access_time()
            
            # Save updated access time
            await self.update_secret(secret, environment)
            
            return secret
            
        except FileNotFoundError:
            return None
        except Exception as e:
            raise BackendError(f"Failed to retrieve secret: {str(e)}", "LocalAdapter")
    
    async def update_secret(self, secret: Secret, environment: Environment) -> bool:
        """Update an existing secret."""
        try:
            secret_file = self.storage_path / environment.name / f"{secret.id}.json"
            
            if not secret_file.exists():
                raise NotFoundError(f"Secret {secret.id} not found", "LocalAdapter")
            
            # Encrypt and save updated secret
            secret_json = secret.model_dump_json()
            encrypted_data = self._encrypt_data(secret_json)
            
            with open(secret_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BackendError(f"Failed to update secret: {str(e)}", "LocalAdapter")
    
    async def delete_secret(self, secret_id: str, environment: Environment) -> bool:
        """Delete a secret from local storage."""
        try:
            secret_file = self.storage_path / environment.name / f"{secret_id}.json"
            
            if not secret_file.exists():
                raise NotFoundError(f"Secret {secret_id} not found", "LocalAdapter")
            
            # Move to deleted folder instead of permanent deletion
            deleted_path = self.storage_path / environment.name / 'deleted'
            deleted_path.mkdir(exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            deleted_file = deleted_path / f"{secret_id}_{timestamp}.json"
            
            secret_file.rename(deleted_file)
            
            return True
            
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BackendError(f"Failed to delete secret: {str(e)}", "LocalAdapter")
    
    async def list_secrets(self, environment: Environment, 
                          filters: Optional[Dict[str, Any]] = None) -> List[Secret]:
        """List secrets in the environment."""
        try:
            env_path = self.storage_path / environment.name
            
            if not env_path.exists():
                return []
            
            secrets = []
            
            for secret_file in env_path.glob("*.json"):
                if secret_file.name.startswith('.'):
                    continue
                
                try:
                    with open(secret_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    decrypted_data = self._decrypt_data(encrypted_data)
                    secret = Secret.model_validate_json(decrypted_data)
                    
                    # Apply filters if provided
                    if filters:
                        if not self._matches_filters(secret, filters):
                            continue
                    
                    secrets.append(secret)
                    
                except Exception:
                    # Skip corrupted files
                    continue
            
            return secrets
            
        except Exception as e:
            raise BackendError(f"Failed to list secrets: {str(e)}", "LocalAdapter")
    
    async def rotate_secret(self, secret_id: str, new_value: str, 
                           environment: Environment) -> bool:
        """Rotate a secret to a new value."""
        try:
            secret = await self.retrieve_secret(secret_id, environment)
            
            if not secret:
                raise NotFoundError(f"Secret {secret_id} not found", "LocalAdapter")
            
            # Update secret with new value
            secret.complete_rotation(new_value)
            
            # Save updated secret
            await self.update_secret(secret, environment)
            
            return True
            
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BackendError(f"Failed to rotate secret: {str(e)}", "LocalAdapter")
    
    async def get_secret_versions(self, secret_id: str, 
                                 environment: Environment) -> List[Dict[str, Any]]:
        """Get version history for a secret (limited in local adapter)."""
        try:
            # Local adapter has limited versioning - return current version only
            secret = await self.retrieve_secret(secret_id, environment)
            
            if not secret:
                return []
            
            return [{
                'version': 1,
                'created_at': secret.metadata.created_at.isoformat(),
                'created_by': secret.metadata.created_by,
                'rotation_count': secret.metadata.rotation_count,
                'last_rotated': secret.metadata.last_rotated.isoformat() if secret.metadata.last_rotated else None,
            }]
            
        except Exception as e:
            raise BackendError(f"Failed to get secret versions: {str(e)}", "LocalAdapter")
    
    async def backup_secrets(self, environment: Environment, backup_path: str) -> bool:
        """Create a backup of secrets for an environment."""
        try:
            env_path = self.storage_path / environment.name
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{environment.name}_backup_{timestamp}.tar.gz"
            
            # Create tar.gz backup
            import tarfile
            with tarfile.open(backup_file, 'w:gz') as tar:
                tar.add(env_path, arcname=environment.name)
            
            return True
            
        except Exception as e:
            raise BackendError(f"Failed to backup secrets: {str(e)}", "LocalAdapter")
    
    async def restore_secrets(self, environment: Environment, backup_path: str) -> bool:
        """Restore secrets from a backup."""
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                raise NotFoundError(f"Backup file {backup_path} not found", "LocalAdapter")
            
            # Extract backup
            import tarfile
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(self.storage_path.parent)
            
            return True
            
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BackendError(f"Failed to restore secrets: {str(e)}", "LocalAdapter")
    
    async def _initialize_encryption(self) -> None:
        """Initialize simple encryption (for demo purposes - use proper crypto in production)."""
        if self._master_key:
            # Use provided master key
            key = self._master_key.encode()
        else:
            # Generate or load master key
            key_file = self.storage_path / '.master_key'
            
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key (simple demo key)
                key = hashlib.sha256(b"demo_key_" + str(datetime.utcnow()).encode()).digest()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # Secure the key file
                os.chmod(key_file, 0o600)
        
        self._cipher_key = key
    
    def _encrypt_data(self, data: str) -> bytes:
        """Simple XOR encryption (for demo purposes - use proper crypto in production)."""
        if not hasattr(self, '_cipher_key'):
            raise BackendError("Encryption not initialized", "LocalAdapter")
        
        data_bytes = data.encode('utf-8')
        key_bytes = self._cipher_key
        
        # Simple XOR encryption
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        # Base64 encode for storage
        return base64.b64encode(bytes(encrypted))
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Simple XOR decryption (for demo purposes - use proper crypto in production)."""
        if not hasattr(self, '_cipher_key'):
            raise BackendError("Encryption not initialized", "LocalAdapter")
        
        # Base64 decode
        try:
            decoded_data = base64.b64decode(encrypted_data)
        except Exception:
            raise BackendError("Invalid encrypted data format", "LocalAdapter")
        
        key_bytes = self._cipher_key
        
        # Simple XOR decryption
        decrypted = bytearray()
        for i, byte in enumerate(decoded_data):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return bytes(decrypted).decode('utf-8')
    
    def _matches_filters(self, secret: Secret, filters: Dict[str, Any]) -> bool:
        """Check if secret matches the provided filters."""
        for key, value in filters.items():
            if key == 'name_pattern':
                import fnmatch
                if not fnmatch.fnmatch(secret.name, value):
                    return False
            elif key == 'secret_type':
                if secret.secret_type != value:
                    return False
            elif key == 'status':
                if secret.status != value:
                    return False
            elif key == 'tags':
                for tag_key, tag_value in value.items():
                    if secret.metadata.tags.get(tag_key) != tag_value:
                        return False
        
        return True
    
    async def _create_backup(self, secret: Secret, environment: Environment) -> None:
        """Create automatic backup of a secret."""
        if not self.backup_enabled:
            return
        
        backup_path = self.storage_path / environment.name / 'backups'
        backup_path.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_path / f"{secret.id}_{timestamp}.json"
        
        # Store encrypted backup
        secret_json = secret.model_dump_json()
        encrypted_data = self._encrypt_data(secret_json)
        
        with open(backup_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Clean up old backups
        await self._cleanup_old_backups(backup_path)
    
    async def _cleanup_old_backups(self, backup_path: Path) -> None:
        """Clean up old backup files."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.backup_retention_days)
        
        for backup_file in backup_path.glob("*.json"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
    
    def _serialize_for_json(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if isinstance(data, dict):
            return {key: self._serialize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, '__dict__'):
            # Handle dataclass or object with attributes
            return self._serialize_for_json(data.__dict__)
        else:
            return data
    
    def _deserialize_from_json(self, data: Any) -> Any:
        """Convert JSON data back to proper types."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str) and self._is_iso_datetime(value):
                    try:
                        result[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        result[key] = value
                else:
                    result[key] = self._deserialize_from_json(value)
            return result
        elif isinstance(data, list):
            return [self._deserialize_from_json(item) for item in data]
        else:
            return data
    
    def _is_iso_datetime(self, value: str) -> bool:
        """Check if string looks like ISO datetime format."""
        if not isinstance(value, str) or len(value) < 19:
            return False
        # Simple check for ISO format pattern
        return 'T' in value and (':' in value) and (len(value) >= 19)