"""Cluster configuration templates for different use cases."""

from typing import Dict, Any, List
from ..config.models import ClusterConfig


class ClusterTemplates:
    """Provides pre-configured cluster templates for different scenarios."""
    
    @staticmethod
    def minimal_dev() -> Dict[str, Any]:
        """Minimal development cluster with single node.
        
        Returns:
            Kind configuration for minimal development setup
        """
        return {
            'kind': 'Cluster',
            'apiVersion': 'kind.x-k8s.io/v1alpha4',
            'name': 'gke-local-minimal',
            'nodes': [
                {
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
                            'hostPort': 80,
                            'protocol': 'TCP'
                        },
                        {
                            'containerPort': 443,
                            'hostPort': 443,
                            'protocol': 'TCP'
                        }
                    ]
                }
            ],
            'networking': {
                'apiServerAddress': '127.0.0.1',
                'apiServerPort': 6443,
                'podSubnet': '10.244.0.0/16',
                'serviceSubnet': '10.96.0.0/16'
            }
        }
    
    @staticmethod
    def ai_optimized() -> Dict[str, Any]:
        """AI-optimized cluster with GPU support and larger nodes.
        
        Returns:
            Kind configuration optimized for AI workloads
        """
        return {
            'kind': 'Cluster',
            'apiVersion': 'kind.x-k8s.io/v1alpha4',
            'name': 'gke-local-ai',
            'nodes': [
                {
                    'role': 'control-plane',
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'InitConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'ingress-ready=true,ai-optimized=true'
                                }
                            }
                        }
                    ],
                    'extraPortMappings': [
                        {
                            'containerPort': 80,
                            'hostPort': 80,
                            'protocol': 'TCP'
                        },
                        {
                            'containerPort': 443,
                            'hostPort': 443,
                            'protocol': 'TCP'
                        },
                        {
                            'containerPort': 8080,
                            'hostPort': 8080,
                            'protocol': 'TCP'
                        }
                    ]
                },
                {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'ai-worker',
                        'gpu-support': 'true'
                    },
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'JoinConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'ai-worker=true,gpu-support=true'
                                }
                            }
                        }
                    ]
                },
                {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'ai-worker',
                        'cpu-intensive': 'true'
                    },
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'JoinConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'ai-worker=true,cpu-intensive=true'
                                }
                            }
                        }
                    ]
                }
            ],
            'networking': {
                'apiServerAddress': '127.0.0.1',
                'apiServerPort': 6443,
                'podSubnet': '10.244.0.0/16',
                'serviceSubnet': '10.96.0.0/16'
            },
            'featureGates': {
                'EphemeralContainers': True,
                'PodSecurity': True,
                'NetworkPolicy': True,
                'DevicePlugins': True  # For GPU support
            }
        }
    
    @staticmethod
    def multi_node_staging() -> Dict[str, Any]:
        """Multi-node cluster simulating staging environment.
        
        Returns:
            Kind configuration for staging-like environment
        """
        return {
            'kind': 'Cluster',
            'apiVersion': 'kind.x-k8s.io/v1alpha4',
            'name': 'gke-local-staging',
            'nodes': [
                {
                    'role': 'control-plane',
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'InitConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'ingress-ready=true,environment=staging'
                                }
                            }
                        }
                    ],
                    'extraPortMappings': [
                        {
                            'containerPort': 80,
                            'hostPort': 80,
                            'protocol': 'TCP'
                        },
                        {
                            'containerPort': 443,
                            'hostPort': 443,
                            'protocol': 'TCP'
                        }
                    ]
                }
            ] + [
                {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'worker',
                        'zone': f'zone-{i % 3 + 1}',  # Simulate 3 zones
                        'worker-id': str(i + 1)
                    },
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'JoinConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': f'worker-id={i + 1},zone=zone-{i % 3 + 1},environment=staging'
                                }
                            }
                        }
                    ]
                }
                for i in range(5)  # 5 worker nodes
            ],
            'networking': {
                'apiServerAddress': '127.0.0.1',
                'apiServerPort': 6443,
                'podSubnet': '10.244.0.0/16',
                'serviceSubnet': '10.96.0.0/16'
            },
            'featureGates': {
                'EphemeralContainers': True,
                'PodSecurity': True,
                'NetworkPolicy': True,
                'TopologyManager': True
            }
        }
    
    @staticmethod
    def autopilot_simulation() -> Dict[str, Any]:
        """Cluster configured to simulate GKE Autopilot behavior.
        
        Returns:
            Kind configuration that mimics GKE Autopilot
        """
        return {
            'kind': 'Cluster',
            'apiVersion': 'kind.x-k8s.io/v1alpha4',
            'name': 'gke-local-autopilot',
            'nodes': [
                {
                    'role': 'control-plane',
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'InitConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'ingress-ready=true,autopilot-mode=true'
                                }
                            }
                        },
                        {
                            'kind': 'ClusterConfiguration',
                            'apiServer': {
                                'extraArgs': {
                                    'enable-admission-plugins': 'NodeRestriction,ResourceQuota,PodSecurity'
                                }
                            }
                        }
                    ],
                    'extraPortMappings': [
                        {
                            'containerPort': 80,
                            'hostPort': 80,
                            'protocol': 'TCP'
                        },
                        {
                            'containerPort': 443,
                            'hostPort': 443,
                            'protocol': 'TCP'
                        }
                    ]
                },
                {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'autopilot-worker',
                        'autopilot-optimized': 'true'
                    },
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'JoinConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'autopilot-worker=true,optimized=true',
                                    'enforce-node-allocatable': 'pods',
                                    'kube-reserved': 'cpu=100m,memory=128Mi',
                                    'system-reserved': 'cpu=100m,memory=128Mi'
                                }
                            }
                        }
                    ]
                },
                {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'autopilot-worker',
                        'autopilot-optimized': 'true'
                    },
                    'kubeadmConfigPatches': [
                        {
                            'kind': 'JoinConfiguration',
                            'nodeRegistration': {
                                'kubeletExtraArgs': {
                                    'node-labels': 'autopilot-worker=true,optimized=true',
                                    'enforce-node-allocatable': 'pods',
                                    'kube-reserved': 'cpu=100m,memory=128Mi',
                                    'system-reserved': 'cpu=100m,memory=128Mi'
                                }
                            }
                        }
                    ]
                }
            ],
            'networking': {
                'apiServerAddress': '127.0.0.1',
                'apiServerPort': 6443,
                'podSubnet': '10.244.0.0/16',
                'serviceSubnet': '10.96.0.0/16'
            },
            'featureGates': {
                'EphemeralContainers': True,
                'PodSecurity': True,
                'NetworkPolicy': True,
                'TopologyManager': True,
                'ResourceQuotaScope': True
            }
        }
    
    @staticmethod
    def get_template(template_name: str) -> Dict[str, Any]:
        """Get a cluster template by name.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Cluster configuration dictionary
            
        Raises:
            ValueError: If template name is not recognized
        """
        templates = {
            'minimal': ClusterTemplates.minimal_dev,
            'ai': ClusterTemplates.ai_optimized,
            'staging': ClusterTemplates.multi_node_staging,
            'autopilot': ClusterTemplates.autopilot_simulation
        }
        
        if template_name not in templates:
            available = ', '.join(templates.keys())
            raise ValueError(f"Unknown template '{template_name}'. Available: {available}")
        
        return templates[template_name]()
    
    @staticmethod
    def list_templates() -> List[str]:
        """List available cluster templates.
        
        Returns:
            List of available template names
        """
        return ['minimal', 'ai', 'staging', 'autopilot']
    
    @staticmethod
    def customize_template(
        base_template: str, 
        cluster_config: ClusterConfig
    ) -> Dict[str, Any]:
        """Customize a base template with specific configuration.
        
        Args:
            base_template: Name of base template to customize
            cluster_config: Cluster configuration to apply
            
        Returns:
            Customized cluster configuration
        """
        config = ClusterTemplates.get_template(base_template)
        
        # Apply customizations
        config['name'] = cluster_config.name
        
        # Update networking
        if 'networking' in config:
            config['networking']['apiServerPort'] = cluster_config.api_server_port
        
        # Update port mappings for ingress
        for node in config['nodes']:
            if node['role'] == 'control-plane' and 'extraPortMappings' in node:
                for mapping in node['extraPortMappings']:
                    if mapping['containerPort'] == 80:
                        mapping['hostPort'] = cluster_config.ingress_port
        
        # Adjust number of worker nodes
        control_plane_nodes = [n for n in config['nodes'] if n['role'] == 'control-plane']
        worker_nodes = [n for n in config['nodes'] if n['role'] == 'worker']
        
        target_workers = max(0, cluster_config.nodes - len(control_plane_nodes))
        
        if len(worker_nodes) != target_workers:
            # Keep control plane nodes
            config['nodes'] = control_plane_nodes
            
            # Add required number of worker nodes
            for i in range(target_workers):
                worker = {
                    'role': 'worker',
                    'labels': {
                        'node-type': 'worker',
                        'worker-id': str(i + 1)
                    }
                }
                config['nodes'].append(worker)
        
        return config