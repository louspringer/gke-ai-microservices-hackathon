"""Tests for cluster management functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from gke_local.cluster.kind_manager import KindManager, ClusterStatus
from gke_local.cluster.lifecycle import ClusterLifecycleManager, ClusterState
from gke_local.cluster.templates import ClusterTemplates
from gke_local.config.models import GKELocalConfig


@pytest.fixture
def test_config():
    """Create test configuration."""
    return GKELocalConfig(
        project_name="test-project",
        cluster={
            "name": "test-cluster",
            "kubernetes_version": "1.28",
            "nodes": 3
        }
    )


class TestKindManager:
    """Test Kind cluster manager."""
    
    @pytest.mark.asyncio
    async def test_cluster_exists_true(self, test_config):
        """Test cluster existence check when cluster exists."""
        manager = KindManager(test_config)
        
        with patch.object(manager, '_run_command') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="test-cluster\nother-cluster\n"
            )
            
            exists = await manager.cluster_exists()
            assert exists is True
    
    @pytest.mark.asyncio
    async def test_cluster_exists_false(self, test_config):
        """Test cluster existence check when cluster doesn't exist."""
        manager = KindManager(test_config)
        
        with patch.object(manager, '_run_command') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="other-cluster\n"
            )
            
            exists = await manager.cluster_exists()
            assert exists is False
    
    @pytest.mark.asyncio
    async def test_create_cluster_success(self, test_config):
        """Test successful cluster creation."""
        manager = KindManager(test_config)
        
        with patch.object(manager, 'cluster_exists', return_value=False), \
             patch.object(manager, '_run_command') as mock_run, \
             patch.object(manager, '_setup_networking') as mock_setup:
            
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            success = await manager.create_cluster()
            
            assert success is True
            mock_setup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_cluster_already_exists(self, test_config):
        """Test cluster creation when cluster already exists."""
        manager = KindManager(test_config)
        
        with patch.object(manager, 'cluster_exists', return_value=True):
            success = await manager.create_cluster()
            assert success is True
    
    @pytest.mark.asyncio
    async def test_delete_cluster_success(self, test_config):
        """Test successful cluster deletion."""
        manager = KindManager(test_config)
        
        with patch.object(manager, 'cluster_exists', return_value=True), \
             patch.object(manager, '_run_command') as mock_run:
            
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            success = await manager.delete_cluster()
            assert success is True
    
    @pytest.mark.asyncio
    async def test_get_cluster_status_not_exists(self, test_config):
        """Test getting status of non-existent cluster."""
        manager = KindManager(test_config)
        
        with patch.object(manager, 'cluster_exists', return_value=False):
            status = await manager.get_cluster_status()
            
            assert status.name == "test-cluster"
            assert status.exists is False
            assert status.running is False
            assert len(status.nodes) == 0
    
    @pytest.mark.asyncio
    async def test_get_cluster_status_exists(self, test_config):
        """Test getting status of existing cluster."""
        manager = KindManager(test_config)
        
        mock_nodes = [
            {
                'metadata': {'name': 'test-cluster-control-plane'},
                'status': {
                    'conditions': [
                        {'type': 'Ready', 'status': 'True'}
                    ]
                }
            }
        ]
        
        with patch.object(manager, 'cluster_exists', return_value=True), \
             patch.object(manager, '_get_cluster_nodes', return_value=mock_nodes), \
             patch.object(manager, '_get_kubeconfig_path', return_value='/path/to/kubeconfig'):
            
            status = await manager.get_cluster_status()
            
            assert status.exists is True
            assert status.running is True
            assert len(status.nodes) == 1
            assert status.kubeconfig_path == '/path/to/kubeconfig'
    
    def test_generate_kind_config(self, test_config):
        """Test Kind configuration generation."""
        manager = KindManager(test_config)
        config = manager._generate_kind_config()
        
        assert config['name'] == 'test-cluster'
        assert config['kind'] == 'Cluster'
        assert len(config['nodes']) == 3  # 1 control plane + 2 workers
        
        # Check control plane node
        control_plane = config['nodes'][0]
        assert control_plane['role'] == 'control-plane'
        assert 'extraPortMappings' in control_plane
        
        # Check worker nodes
        workers = [n for n in config['nodes'] if n['role'] == 'worker']
        assert len(workers) == 2


class TestClusterLifecycleManager:
    """Test cluster lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, test_config):
        """Test successful initialization."""
        manager = ClusterLifecycleManager(test_config)
        
        with patch.object(manager, '_update_state') as mock_update:
            success = await manager.initialize()
            
            assert success is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_and_start_success(self, test_config):
        """Test successful cluster creation and startup."""
        manager = ClusterLifecycleManager(test_config)
        
        with patch.object(manager.kind_manager, 'create_cluster', return_value=True), \
             patch.object(manager, '_wait_for_ready') as mock_wait, \
             patch.object(manager, 'start_monitoring') as mock_monitor:
            
            # Simulate successful ready state
            async def set_ready():
                manager._state = ClusterState.READY
            
            mock_wait.side_effect = set_ready
            
            success = await manager.create_and_start()
            
            assert success is True
            assert manager.state == ClusterState.READY
            mock_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_and_start_failure(self, test_config):
        """Test cluster creation failure."""
        manager = ClusterLifecycleManager(test_config)
        
        with patch.object(manager.kind_manager, 'create_cluster', return_value=False):
            success = await manager.create_and_start()
            
            assert success is False
            assert manager.state == ClusterState.ERROR
    
    @pytest.mark.asyncio
    async def test_stop_and_cleanup_success(self, test_config):
        """Test successful cluster cleanup."""
        manager = ClusterLifecycleManager(test_config)
        
        with patch.object(manager, 'stop_monitoring') as mock_stop, \
             patch.object(manager.kind_manager, 'delete_cluster', return_value=True):
            
            success = await manager.stop_and_cleanup()
            
            assert success is True
            assert manager.state == ClusterState.NOT_EXISTS
            mock_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_success(self, test_config):
        """Test successful cluster reset."""
        manager = ClusterLifecycleManager(test_config)
        
        with patch.object(manager, 'stop_and_cleanup', return_value=True), \
             patch.object(manager, 'create_and_start', return_value=True):
            
            success = await manager.reset()
            assert success is True
    
    @pytest.mark.asyncio
    async def test_wait_for_ready_success(self, test_config):
        """Test waiting for cluster to be ready."""
        manager = ClusterLifecycleManager(test_config)
        
        call_count = 0
        
        async def mock_get_status():
            nonlocal call_count
            call_count += 1
            
            if call_count >= 2:  # Ready on second call
                return ClusterStatus(
                    name="test-cluster",
                    exists=True,
                    running=True,
                    nodes=[{'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}]
                )
            else:
                return ClusterStatus(
                    name="test-cluster",
                    exists=True,
                    running=False,
                    nodes=[]
                )
        
        with patch.object(manager, 'get_status', side_effect=mock_get_status):
            success = await manager.wait_for_ready(timeout=10)
            
            assert success is True
            assert manager.state == ClusterState.READY
    
    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self, test_config):
        """Test timeout while waiting for cluster."""
        manager = ClusterLifecycleManager(test_config)
        
        # Always return not ready
        mock_status = ClusterStatus(
            name="test-cluster",
            exists=True,
            running=False,
            nodes=[]
        )
        
        with patch.object(manager, 'get_status', return_value=mock_status):
            success = await manager.wait_for_ready(timeout=1)
            
            assert success is False
    
    def test_event_handlers(self, test_config):
        """Test event handler management."""
        manager = ClusterLifecycleManager(test_config)
        
        handler1 = Mock()
        handler2 = Mock()
        
        # Add handlers
        manager.add_event_handler('test_event', handler1)
        manager.add_event_handler('test_event', handler2)
        
        assert len(manager._event_handlers['test_event']) == 2
        
        # Remove handler
        manager.remove_event_handler('test_event', handler1)
        
        assert len(manager._event_handlers['test_event']) == 1
        assert handler2 in manager._event_handlers['test_event']


class TestClusterTemplates:
    """Test cluster templates."""
    
    def test_list_templates(self):
        """Test listing available templates."""
        templates = ClusterTemplates.list_templates()
        
        assert 'minimal' in templates
        assert 'ai' in templates
        assert 'staging' in templates
        assert 'autopilot' in templates
    
    def test_get_template_minimal(self):
        """Test getting minimal template."""
        config = ClusterTemplates.get_template('minimal')
        
        assert config['name'] == 'gke-local-minimal'
        assert len(config['nodes']) == 1
        assert config['nodes'][0]['role'] == 'control-plane'
    
    def test_get_template_ai(self):
        """Test getting AI template."""
        config = ClusterTemplates.get_template('ai')
        
        assert config['name'] == 'gke-local-ai'
        assert len(config['nodes']) == 3  # 1 control plane + 2 workers
        
        # Check for AI-specific features
        workers = [n for n in config['nodes'] if n['role'] == 'worker']
        assert len(workers) == 2
        
        # Check feature gates
        assert 'DevicePlugins' in config['featureGates']
    
    def test_get_template_invalid(self):
        """Test getting invalid template."""
        with pytest.raises(ValueError, match="Unknown template"):
            ClusterTemplates.get_template('invalid')
    
    def test_customize_template(self, test_config):
        """Test template customization."""
        config = ClusterTemplates.customize_template('minimal', test_config.cluster)
        
        assert config['name'] == 'test-cluster'
        assert config['networking']['apiServerPort'] == test_config.cluster.api_server_port
        
        # Check port mapping customization
        control_plane = config['nodes'][0]
        port_mappings = control_plane['extraPortMappings']
        http_mapping = next(m for m in port_mappings if m['containerPort'] == 80)
        assert http_mapping['hostPort'] == test_config.cluster.ingress_port