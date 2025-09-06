"""Local container registry management for fast image storage and development."""

import asyncio
import json
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..config.models import GKELocalConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RegistryStatus:
    """Represents the current status of the local registry."""
    name: str
    running: bool
    port: int
    host: str
    container_id: Optional[str] = None
    
    @property
    def endpoint(self) -> str:
        """Get the registry endpoint URL."""
        return f"{self.host}:{self.port}"
    
    @property
    def is_accessible(self) -> bool:
        """Check if registry is accessible."""
        return self.running and self.container_id is not None


class LocalRegistryManager:
    """Manages local Docker registry for fast image storage and development."""
    
    def __init__(self, config: GKELocalConfig):
        """Initialize registry manager with configuration.
        
        Args:
            config: GKE Local configuration
        """
        self.config = config
        self.cluster_config = config.cluster
        self.registry_name = f"{self.cluster_config.name}-registry"
        self.registry_port = self.cluster_config.registry_port
        self.registry_host = "localhost"
        
    async def start_registry(self) -> bool:
        """Start the local Docker registry.
        
        Returns:
            True if registry started successfully, False otherwise
        """
        logger.info(f"Starting local registry: {self.registry_name}")
        
        try:
            # Check if registry is already running
            status = await self.get_registry_status()
            if status.running:
                logger.info(f"Registry {self.registry_name} is already running")
                return True
            
            # Remove existing stopped container if it exists
            await self._remove_existing_container()
            
            # Start new registry container
            cmd = [
                'docker', 'run', '-d',
                '--name', self.registry_name,
                '--restart', 'unless-stopped',
                '-p', f'{self.registry_port}:5000',
                '-e', 'REGISTRY_STORAGE_DELETE_ENABLED=true',
                'registry:2'
            ]
            
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(f"Successfully started registry: {self.registry_name} ({container_id[:12]})")
                
                # Wait for registry to be ready
                await self._wait_for_registry_ready()
                
                # Connect registry to Kind network if cluster exists
                await self._connect_to_kind_network()
                
                return True
            else:
                logger.error(f"Failed to start registry: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting registry: {e}")
            return False
    
    async def stop_registry(self) -> bool:
        """Stop the local Docker registry.
        
        Returns:
            True if registry stopped successfully, False otherwise
        """
        logger.info(f"Stopping local registry: {self.registry_name}")
        
        try:
            status = await self.get_registry_status()
            if not status.running:
                logger.info(f"Registry {self.registry_name} is not running")
                return True
            
            # Stop the container
            cmd = ['docker', 'stop', self.registry_name]
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully stopped registry: {self.registry_name}")
                return True
            else:
                logger.error(f"Failed to stop registry: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping registry: {e}")
            return False
    
    async def remove_registry(self) -> bool:
        """Remove the local Docker registry container.
        
        Returns:
            True if registry removed successfully, False otherwise
        """
        logger.info(f"Removing local registry: {self.registry_name}")
        
        try:
            # Stop first if running
            await self.stop_registry()
            
            # Remove the container
            await self._remove_existing_container()
            
            logger.info(f"Successfully removed registry: {self.registry_name}")
            return True
                
        except Exception as e:
            logger.error(f"Error removing registry: {e}")
            return False
    
    async def get_registry_status(self) -> RegistryStatus:
        """Get detailed status of the local registry.
        
        Returns:
            RegistryStatus object with current registry state
        """
        try:
            # Check if container exists and is running
            cmd = [
                'docker', 'ps', '-a',
                '--filter', f'name={self.registry_name}',
                '--format', '{{.ID}}\t{{.Status}}\t{{.Ports}}'
            ]
            
            result = await self._run_command(cmd)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        container_id = parts[0]
                        status_text = parts[1]
                        running = status_text.startswith('Up')
                        
                        return RegistryStatus(
                            name=self.registry_name,
                            running=running,
                            port=self.registry_port,
                            host=self.registry_host,
                            container_id=container_id
                        )
            
            # Registry doesn't exist
            return RegistryStatus(
                name=self.registry_name,
                running=False,
                port=self.registry_port,
                host=self.registry_host
            )
            
        except Exception as e:
            logger.error(f"Error getting registry status: {e}")
            return RegistryStatus(
                name=self.registry_name,
                running=False,
                port=self.registry_port,
                host=self.registry_host
            )
    
    async def push_image(self, local_image: str, registry_tag: Optional[str] = None) -> bool:
        """Push an image to the local registry.
        
        Args:
            local_image: Local image name/tag to push
            registry_tag: Optional registry tag, defaults to same as local image
            
        Returns:
            True if push successful, False otherwise
        """
        if registry_tag is None:
            registry_tag = local_image
        
        registry_image = f"{self.registry_host}:{self.registry_port}/{registry_tag}"
        
        logger.info(f"Pushing image {local_image} to registry as {registry_image}")
        
        try:
            # Tag the image for the registry
            tag_cmd = ['docker', 'tag', local_image, registry_image]
            tag_result = await self._run_command(tag_cmd)
            
            if tag_result.returncode != 0:
                logger.error(f"Failed to tag image: {tag_result.stderr}")
                return False
            
            # Push the image
            push_cmd = ['docker', 'push', registry_image]
            push_result = await self._run_command(push_cmd)
            
            if push_result.returncode == 0:
                logger.info(f"Successfully pushed image: {registry_image}")
                return True
            else:
                logger.error(f"Failed to push image: {push_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error pushing image: {e}")
            return False
    
    async def pull_image(self, registry_tag: str, local_tag: Optional[str] = None) -> bool:
        """Pull an image from the local registry.
        
        Args:
            registry_tag: Registry image tag to pull
            local_tag: Optional local tag, defaults to same as registry tag
            
        Returns:
            True if pull successful, False otherwise
        """
        registry_image = f"{self.registry_host}:{self.registry_port}/{registry_tag}"
        
        logger.info(f"Pulling image {registry_image} from registry")
        
        try:
            # Pull the image
            pull_cmd = ['docker', 'pull', registry_image]
            pull_result = await self._run_command(pull_cmd)
            
            if pull_result.returncode != 0:
                logger.error(f"Failed to pull image: {pull_result.stderr}")
                return False
            
            # Tag with local name if specified
            if local_tag and local_tag != registry_tag:
                tag_cmd = ['docker', 'tag', registry_image, local_tag]
                tag_result = await self._run_command(tag_cmd)
                
                if tag_result.returncode != 0:
                    logger.error(f"Failed to tag pulled image: {tag_result.stderr}")
                    return False
            
            logger.info(f"Successfully pulled image: {registry_image}")
            return True
                
        except Exception as e:
            logger.error(f"Error pulling image: {e}")
            return False
    
    async def list_images(self) -> List[Dict[str, Any]]:
        """List images in the local registry.
        
        Returns:
            List of image information dictionaries
        """
        try:
            # Use registry API to list repositories
            import aiohttp
            
            status = await self.get_registry_status()
            if not status.is_accessible:
                logger.warning("Registry is not accessible")
                return []
            
            async with aiohttp.ClientSession() as session:
                # Get list of repositories
                repos_url = f"http://{status.endpoint}/v2/_catalog"
                async with session.get(repos_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        repositories = data.get('repositories', [])
                        
                        images = []
                        for repo in repositories:
                            # Get tags for each repository
                            tags_url = f"http://{status.endpoint}/v2/{repo}/tags/list"
                            async with session.get(tags_url) as tags_response:
                                if tags_response.status == 200:
                                    tags_data = await tags_response.json()
                                    tags = tags_data.get('tags', [])
                                    
                                    for tag in tags:
                                        images.append({
                                            'repository': repo,
                                            'tag': tag,
                                            'full_name': f"{repo}:{tag}",
                                            'registry_url': f"{status.endpoint}/{repo}:{tag}"
                                        })
                        
                        return images
                    else:
                        logger.error(f"Failed to list repositories: HTTP {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error listing images: {e}")
            return []
    
    async def cleanup_images(self, keep_latest: int = 5) -> bool:
        """Clean up old images in the registry.
        
        Args:
            keep_latest: Number of latest images to keep per repository
            
        Returns:
            True if cleanup successful, False otherwise
        """
        logger.info(f"Cleaning up registry images (keeping latest {keep_latest})")
        
        try:
            images = await self.list_images()
            
            # Group images by repository
            repos = {}
            for image in images:
                repo = image['repository']
                if repo not in repos:
                    repos[repo] = []
                repos[repo].append(image)
            
            # For each repository, keep only the latest images
            deleted_count = 0
            for repo, repo_images in repos.items():
                if len(repo_images) > keep_latest:
                    # Sort by tag (simple string sort, could be improved)
                    repo_images.sort(key=lambda x: x['tag'], reverse=True)
                    
                    # Delete older images
                    for image in repo_images[keep_latest:]:
                        if await self._delete_image_manifest(repo, image['tag']):
                            deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old images from registry")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up images: {e}")
            return False
    
    async def _wait_for_registry_ready(self, timeout: int = 30) -> bool:
        """Wait for registry to be ready to accept requests.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if registry becomes ready, False if timeout
        """
        import aiohttp
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                logger.error("Timeout waiting for registry to be ready")
                return False
            
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"http://{self.registry_host}:{self.registry_port}/v2/"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            logger.info("Registry is ready")
                            return True
            except Exception:
                pass  # Registry not ready yet
            
            await asyncio.sleep(2)
    
    async def _connect_to_kind_network(self) -> None:
        """Connect registry to Kind network for cluster access."""
        try:
            # Check if Kind network exists
            network_name = "kind"
            
            cmd = ['docker', 'network', 'ls', '--filter', f'name={network_name}', '--format', '{{.Name}}']
            result = await self._run_command(cmd)
            
            if result.returncode == 0 and network_name in result.stdout:
                # Connect registry to Kind network
                connect_cmd = ['docker', 'network', 'connect', network_name, self.registry_name]
                connect_result = await self._run_command(connect_cmd)
                
                if connect_result.returncode == 0:
                    logger.info(f"Connected registry to Kind network: {network_name}")
                else:
                    logger.warning(f"Failed to connect registry to Kind network: {connect_result.stderr}")
            else:
                logger.info("Kind network not found, skipping network connection")
                
        except Exception as e:
            logger.warning(f"Error connecting registry to Kind network: {e}")
    
    async def _remove_existing_container(self) -> None:
        """Remove existing registry container if it exists."""
        try:
            cmd = ['docker', 'rm', '-f', self.registry_name]
            await self._run_command(cmd)
        except Exception:
            pass  # Container might not exist
    
    async def _delete_image_manifest(self, repository: str, tag: str) -> bool:
        """Delete an image manifest from the registry.
        
        Args:
            repository: Repository name
            tag: Image tag
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            import aiohttp
            
            status = await self.get_registry_status()
            if not status.is_accessible:
                return False
            
            async with aiohttp.ClientSession() as session:
                # Get manifest digest
                manifest_url = f"http://{status.endpoint}/v2/{repository}/manifests/{tag}"
                headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
                
                async with session.head(manifest_url, headers=headers) as response:
                    if response.status == 200:
                        digest = response.headers.get('Docker-Content-Digest')
                        if digest:
                            # Delete manifest
                            delete_url = f"http://{status.endpoint}/v2/{repository}/manifests/{digest}"
                            async with session.delete(delete_url) as delete_response:
                                return delete_response.status == 202
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting image manifest: {e}")
            return False
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command asynchronously.
        
        Args:
            cmd: Command and arguments to run
            
        Returns:
            CompletedProcess with result
        """
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode('utf-8'),
            stderr=stderr.decode('utf-8')
        )


class RegistryIntegration:
    """Integration utilities for connecting registry with Kind clusters."""
    
    def __init__(self, registry_manager: LocalRegistryManager):
        """Initialize registry integration.
        
        Args:
            registry_manager: Local registry manager instance
        """
        self.registry_manager = registry_manager
        self.config = registry_manager.config
    
    async def setup_cluster_registry_connection(self, cluster_name: str) -> bool:
        """Set up registry connection for a Kind cluster.
        
        Args:
            cluster_name: Name of the Kind cluster
            
        Returns:
            True if setup successful, False otherwise
        """
        logger.info(f"Setting up registry connection for cluster: {cluster_name}")
        
        try:
            # Create registry connection configuration
            registry_config = self._create_registry_config()
            
            # Apply configuration to cluster
            success = await self._apply_registry_config(cluster_name, registry_config)
            
            if success:
                logger.info(f"Successfully configured registry connection for cluster: {cluster_name}")
                return True
            else:
                logger.error(f"Failed to configure registry connection for cluster: {cluster_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up registry connection: {e}")
            return False
    
    def _create_registry_config(self) -> Dict[str, Any]:
        """Create registry connection configuration.
        
        Returns:
            Registry configuration dictionary
        """
        registry_status = asyncio.run(self.registry_manager.get_registry_status())
        
        return {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'local-registry-hosting',
                'namespace': 'kube-public'
            },
            'data': {
                'localRegistryHosting.v1': json.dumps({
                    'host': f"{registry_status.host}:{registry_status.port}",
                    'hostFromContainerRuntime': f"{self.registry_manager.registry_name}:5000",
                    'help': 'https://kind.sigs.k8s.io/docs/user/local-registry/'
                })
            }
        }
    
    async def _apply_registry_config(self, cluster_name: str, config: Dict[str, Any]) -> bool:
        """Apply registry configuration to cluster.
        
        Args:
            cluster_name: Name of the Kind cluster
            config: Registry configuration
            
        Returns:
            True if application successful, False otherwise
        """
        try:
            # Write config to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(config, f)
                config_path = f.name
            
            try:
                # Apply configuration
                cmd = [
                    'kubectl', 'apply', '-f', config_path,
                    '--context', f'kind-{cluster_name}'
                ]
                
                result = await self.registry_manager._run_command(cmd)
                
                return result.returncode == 0
                
            finally:
                # Clean up temporary file
                Path(config_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Error applying registry config: {e}")
            return False