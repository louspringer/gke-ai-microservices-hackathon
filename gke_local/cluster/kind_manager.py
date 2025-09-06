"""Kind cluster management utilities for local GKE development."""

import asyncio
import json
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..config.models import GKELocalConfig, ClusterConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ClusterStatus:
    """Represents the current status of a Kind cluster."""
    name: str
    exists: bool
    running: bool
    nodes: List[Dict[str, Any]]
    kubeconfig_path: Optional[str] = None
    
    @property
    def is_ready(self) -> bool:
        """Check if cluster is ready for use."""
        return self.exists and self.running and len(self.nodes) > 0


class KindManager:
    """Manages Kind cluster lifecycle for local GKE development."""
    
    def __init__(self, config: GKELocalConfig):
        """Initialize Kind manager with configuration.
        
        Args:
            config: GKE Local configuration
        """
        self.config = config
        self.cluster_config = config.cluster
        self.cluster_name = self.cluster_config.name
        
    async def create_cluster(self) -> bool:
        """Create a new Kind cluster with proper networking configuration.
        
        Returns:
            True if cluster was created successfully, False otherwise
        """
        logger.info(f"Creating Kind cluster: {self.cluster_name}")
        
        try:
            # Check if cluster already exists
            if await self.cluster_exists():
                logger.info(f"Cluster {self.cluster_name} already exists")
                return True
            
            # Generate Kind configuration
            kind_config = self._generate_kind_config()
            
            # Write config to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(kind_config, f, default_flow_style=False)
                config_path = f.name
            
            try:
                # Create cluster with configuration
                cmd = [
                    'kind', 'create', 'cluster',
                    '--name', self.cluster_name,
                    '--config', config_path,
                    '--wait', '300s'  # Wait up to 5 minutes for cluster to be ready
                ]
                
                result = await self._run_command(cmd)
                
                if result.returncode == 0:
                    logger.info(f"Successfully created cluster: {self.cluster_name}")
                    
                    # Set up networking
                    await self._setup_networking()
                    
                    return True
                else:
                    logger.error(f"Failed to create cluster: {result.stderr}")
                    return False
                    
            finally:
                # Clean up temporary config file
                Path(config_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Error creating cluster: {e}")
            return False
    
    async def delete_cluster(self) -> bool:
        """Delete the Kind cluster.
        
        Returns:
            True if cluster was deleted successfully, False otherwise
        """
        logger.info(f"Deleting Kind cluster: {self.cluster_name}")
        
        try:
            if not await self.cluster_exists():
                logger.info(f"Cluster {self.cluster_name} does not exist")
                return True
            
            cmd = ['kind', 'delete', 'cluster', '--name', self.cluster_name]
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully deleted cluster: {self.cluster_name}")
                return True
            else:
                logger.error(f"Failed to delete cluster: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting cluster: {e}")
            return False
    
    async def start_cluster(self) -> bool:
        """Start the Kind cluster if it exists but is stopped.
        
        Returns:
            True if cluster is running, False otherwise
        """
        logger.info(f"Starting Kind cluster: {self.cluster_name}")
        
        try:
            status = await self.get_cluster_status()
            
            if not status.exists:
                logger.error(f"Cluster {self.cluster_name} does not exist")
                return False
            
            if status.running:
                logger.info(f"Cluster {self.cluster_name} is already running")
                return True
            
            # Kind doesn't have a direct start command, but we can try to recreate
            # if the cluster exists but isn't running
            logger.info("Kind clusters cannot be started once stopped. Consider recreating.")
            return False
            
        except Exception as e:
            logger.error(f"Error starting cluster: {e}")
            return False
    
    async def stop_cluster(self) -> bool:
        """Stop the Kind cluster.
        
        Note: Kind doesn't support stopping clusters, only deletion.
        This method provides a consistent interface but will log a warning.
        
        Returns:
            True (Kind clusters cannot be stopped, only deleted)
        """
        logger.warning("Kind clusters cannot be stopped, only deleted. Use delete_cluster() instead.")
        return True
    
    async def reset_cluster(self) -> bool:
        """Reset the Kind cluster by deleting and recreating it.
        
        Returns:
            True if cluster was reset successfully, False otherwise
        """
        logger.info(f"Resetting Kind cluster: {self.cluster_name}")
        
        try:
            # Delete existing cluster
            await self.delete_cluster()
            
            # Wait a moment for cleanup
            await asyncio.sleep(2)
            
            # Create new cluster
            return await self.create_cluster()
            
        except Exception as e:
            logger.error(f"Error resetting cluster: {e}")
            return False
    
    async def cluster_exists(self) -> bool:
        """Check if the Kind cluster exists.
        
        Returns:
            True if cluster exists, False otherwise
        """
        try:
            cmd = ['kind', 'get', 'clusters']
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                clusters = result.stdout.strip().split('\n')
                return self.cluster_name in clusters
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking cluster existence: {e}")
            return False
    
    async def get_cluster_status(self) -> ClusterStatus:
        """Get detailed status of the Kind cluster.
        
        Returns:
            ClusterStatus object with current cluster state
        """
        try:
            exists = await self.cluster_exists()
            
            if not exists:
                return ClusterStatus(
                    name=self.cluster_name,
                    exists=False,
                    running=False,
                    nodes=[]
                )
            
            # Get cluster nodes
            nodes = await self._get_cluster_nodes()
            
            # Check if cluster is running (nodes are ready)
            running = len(nodes) > 0 and all(
                node.get('status', {}).get('conditions', [])
                for node in nodes
            )
            
            # Get kubeconfig path
            kubeconfig_path = await self._get_kubeconfig_path()
            
            return ClusterStatus(
                name=self.cluster_name,
                exists=True,
                running=running,
                nodes=nodes,
                kubeconfig_path=kubeconfig_path
            )
            
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            return ClusterStatus(
                name=self.cluster_name,
                exists=False,
                running=False,
                nodes=[]
            )
    
    async def get_kubeconfig(self) -> Optional[str]:
        """Get the kubeconfig for the Kind cluster.
        
        Returns:
            Kubeconfig content as string, or None if cluster doesn't exist
        """
        try:
            if not await self.cluster_exists():
                return None
            
            cmd = ['kind', 'get', 'kubeconfig', '--name', self.cluster_name]
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Failed to get kubeconfig: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting kubeconfig: {e}")
            return None
    
    def _generate_kind_config(self) -> Dict[str, Any]:
        """Generate Kind cluster configuration based on GKE Local config.
        
        Returns:
            Kind configuration dictionary
        """
        # Base configuration
        config = {
            'kind': 'Cluster',
            'apiVersion': 'kind.x-k8s.io/v1alpha4',
            'name': self.cluster_name,
            'nodes': []
        }
        
        # Add control plane node
        control_plane = {
            'role': 'control-plane',
            'kubeadmConfigPatches': [
                {
                    'kind': 'InitConfiguration',
                    'nodeRegistration': {
                        'kubeletExtraArgs': {
                            'node-labels': 'ingress-ready=true'
                        }
                    }
                }
            ],
            'extraPortMappings': [
                {
                    'containerPort': 80,
                    'hostPort': self.cluster_config.ingress_port,
                    'protocol': 'TCP'
                },
                {
                    'containerPort': 443,
                    'hostPort': 443,
                    'protocol': 'TCP'
                }
            ]
        }
        
        config['nodes'].append(control_plane)
        
        # Add worker nodes
        for i in range(max(0, self.cluster_config.nodes - 1)):
            worker = {
                'role': 'worker',
                'labels': {
                    'node-type': 'worker',
                    'worker-id': str(i + 1)
                }
            }
            config['nodes'].append(worker)
        
        # Networking configuration
        config['networking'] = {
            'apiServerAddress': '127.0.0.1',
            'apiServerPort': self.cluster_config.api_server_port,
            'podSubnet': '10.244.0.0/16',
            'serviceSubnet': '10.96.0.0/16'
        }
        
        # Feature gates for GKE Autopilot simulation
        config['featureGates'] = {
            'EphemeralContainers': True,
            'PodSecurity': True,
            'NetworkPolicy': True
        }
        
        return config
    
    async def _setup_networking(self) -> None:
        """Set up networking components after cluster creation."""
        logger.info("Setting up cluster networking")
        
        try:
            # Install CNI (Calico for network policies)
            await self._install_cni()
            
            # Set up local registry connection
            await self._setup_registry_connection()
            
        except Exception as e:
            logger.error(f"Error setting up networking: {e}")
    
    async def _install_cni(self) -> None:
        """Install Container Network Interface (CNI) plugin."""
        logger.info("Installing CNI plugin")
        
        # Use Calico for network policy support
        calico_manifest = "https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml"
        
        cmd = [
            'kubectl', 'apply', '-f', calico_manifest,
            '--context', f'kind-{self.cluster_name}'
        ]
        
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            logger.info("Successfully installed CNI plugin")
        else:
            logger.warning(f"CNI installation may have issues: {result.stderr}")
    
    async def _setup_registry_connection(self) -> None:
        """Set up connection to local container registry."""
        logger.info("Setting up local registry connection")
        
        # Create registry connection configuration
        registry_config = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'local-registry-hosting',
                'namespace': 'kube-public'
            },
            'data': {
                'localRegistryHosting.v1': json.dumps({
                    'host': f'localhost:{self.cluster_config.registry_port}',
                    'help': 'https://kind.sigs.k8s.io/docs/user/local-registry/'
                })
            }
        }
        
        # Apply registry configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(registry_config, f)
            config_path = f.name
        
        try:
            cmd = [
                'kubectl', 'apply', '-f', config_path,
                '--context', f'kind-{self.cluster_name}'
            ]
            
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                logger.info("Successfully configured local registry connection")
            else:
                logger.warning(f"Registry configuration may have issues: {result.stderr}")
                
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    async def _get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """Get information about cluster nodes.
        
        Returns:
            List of node information dictionaries
        """
        try:
            cmd = [
                'kubectl', 'get', 'nodes', '-o', 'json',
                '--context', f'kind-{self.cluster_name}'
            ]
            
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                return nodes_data.get('items', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting cluster nodes: {e}")
            return []
    
    async def _get_kubeconfig_path(self) -> Optional[str]:
        """Get the path to the kubeconfig file.
        
        Returns:
            Path to kubeconfig file, or None if not found
        """
        try:
            # Kind stores kubeconfig in the default location
            kubeconfig_path = Path.home() / '.kube' / 'config'
            
            if kubeconfig_path.exists():
                return str(kubeconfig_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting kubeconfig path: {e}")
            return None
    
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