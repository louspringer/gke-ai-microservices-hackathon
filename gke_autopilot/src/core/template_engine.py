"""
Template Engine for GKE Autopilot Deployment Framework

This module provides Kubernetes manifest template generation with Jinja2,
dynamic resource optimization, and GKE Autopilot-specific best practices.
"""

import logging
import yaml
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from dataclasses import dataclass, field

from ..models.app_config import AppConfig, ClusterConfig, ResourceRequests, ScalingConfig


logger = logging.getLogger(__name__)


@dataclass
class TemplateContext:
    """Context for template rendering"""
    app_config: AppConfig
    cluster_config: Optional[ClusterConfig] = None
    project_id: str = ""
    namespace: str = "default"
    environment: str = "production"
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        context = {
            'app': self.app_config.to_dict(),
            'project_id': self.project_id,
            'namespace': self.namespace,
            'environment': self.environment,
            **self.custom_variables
        }
        
        if self.cluster_config:
            context['cluster'] = self.cluster_config.to_dict()
        
        return context


class TemplateEngine:
    """
    Kubernetes manifest template engine with GKE Autopilot optimizations.
    
    Features:
    - Jinja2-based template rendering
    - Dynamic resource generation based on application requirements
    - GKE Autopilot-specific optimizations and best practices
    - Built-in templates for common deployment patterns
    - Custom template support with validation
    """
    
    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """
        Initialize template engine.
        
        Args:
            template_dir: Directory containing custom templates (optional)
        """
        self.template_dir = Path(template_dir) if template_dir else None
        
        # Setup Jinja2 environment
        if self.template_dir and self.template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=False,  # YAML/JSON don't need HTML escaping
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.jinja_env = Environment(autoescape=False)
        
        # Add custom filters
        self._setup_custom_filters()
        
        # Built-in templates
        self._builtin_templates = self._load_builtin_templates()
        
        logger.info(f"Template engine initialized with template dir: {self.template_dir}")
    
    def _setup_custom_filters(self) -> None:
        """Setup custom Jinja2 filters for Kubernetes manifests"""
        
        def to_yaml(value):
            """Convert value to YAML format"""
            return yaml.dump(value, default_flow_style=False, indent=2)
        
        def to_json(value):
            """Convert value to JSON format"""
            return json.dumps(value, indent=2)
        
        def resource_to_k8s(resource_str: str) -> str:
            """Convert resource string to Kubernetes format"""
            # Ensure proper Kubernetes resource format
            if resource_str.endswith('m'):  # CPU millicores
                return resource_str
            elif any(resource_str.endswith(suffix) for suffix in ['Mi', 'Gi', 'Ki']):  # Memory
                return resource_str
            elif resource_str.replace('.', '').isdigit():  # Plain number
                return f"{resource_str}"
            else:
                return resource_str
        
        def autopilot_optimize_resources(resources: Dict[str, str]) -> Dict[str, str]:
            """Optimize resources for GKE Autopilot"""
            optimized = resources.copy()
            
            # CPU optimization
            cpu = resources.get('cpu', '100m')
            if cpu.endswith('m'):
                cpu_millicores = int(cpu[:-1])
                if cpu_millicores < 250:
                    optimized['cpu'] = '250m'  # Minimum recommended for Autopilot
            
            # Memory optimization
            memory = resources.get('memory', '256Mi')
            if memory.endswith('Mi'):
                memory_mb = int(memory[:-2])
                if memory_mb < 512:
                    optimized['memory'] = '512Mi'  # Minimum recommended for Autopilot
            
            return optimized
        
        def generate_labels(app_name: str, environment: str = "production") -> Dict[str, str]:
            """Generate standard Kubernetes labels"""
            return {
                'app': app_name,
                'app.kubernetes.io/name': app_name,
                'app.kubernetes.io/instance': app_name,
                'app.kubernetes.io/version': '1.0.0',
                'app.kubernetes.io/component': 'application',
                'app.kubernetes.io/part-of': app_name,
                'app.kubernetes.io/managed-by': 'gke-autopilot-framework',
                'environment': environment
            }
        
        def generate_selector_labels(app_name: str) -> Dict[str, str]:
            """Generate selector labels for Kubernetes resources"""
            return {
                'app': app_name,
                'app.kubernetes.io/name': app_name,
                'app.kubernetes.io/instance': app_name
            }
        
        # Register filters
        self.jinja_env.filters['to_yaml'] = to_yaml
        self.jinja_env.filters['to_json'] = to_json
        self.jinja_env.filters['resource_to_k8s'] = resource_to_k8s
        self.jinja_env.filters['autopilot_optimize'] = autopilot_optimize_resources
        self.jinja_env.filters['generate_labels'] = generate_labels
        self.jinja_env.filters['selector_labels'] = generate_selector_labels
    
    def _load_builtin_templates(self) -> Dict[str, str]:
        """Load built-in Kubernetes manifest templates"""
        
        deployment_template = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app.name }}
  namespace: {{ namespace }}
  labels: {{ app.name | generate_labels(environment) | to_yaml | indent(4) }}
  annotations:
    deployment.kubernetes.io/revision: "1"
    gke-autopilot.io/managed: "true"
spec:
  replicas: {{ app.scaling.min_replicas }}
  selector:
    matchLabels: {{ app.name | selector_labels | to_yaml | indent(6) }}
  template:
    metadata:
      labels: {{ app.name | generate_labels(environment) | to_yaml | indent(8) }}
      annotations:
        gke-autopilot.io/resource-adjustment: "true"
    spec:
      containers:
      - name: {{ app.name }}
        image: {{ app.image }}
        ports:
        - containerPort: {{ app.port }}
          name: http
          protocol: TCP
        resources:
          requests: {{ app.resources | autopilot_optimize | to_yaml | indent(12) }}
          limits: {{ app.resources | autopilot_optimize | to_yaml | indent(12) }}
        {% if app.environment_variables %}
        env:
        {% for key, value in app.environment_variables.items() %}
        - name: {{ key }}
          value: "{{ value }}"
        {% endfor %}
        {% endif %}
        readinessProbe:
          httpGet:
            path: {{ app.healthChecks.path }}
            port: {{ app.healthChecks.port }}
          initialDelaySeconds: {{ app.healthChecks.initial_delay_seconds }}
          periodSeconds: {{ app.healthChecks.period_seconds }}
          timeoutSeconds: {{ app.healthChecks.timeout_seconds }}
          failureThreshold: {{ app.healthChecks.failure_threshold }}
          successThreshold: {{ app.healthChecks.success_threshold }}
        livenessProbe:
          httpGet:
            path: {{ app.healthChecks.path }}
            port: {{ app.healthChecks.port }}
          initialDelaySeconds: {{ app.healthChecks.initial_delay_seconds + 30 }}
          periodSeconds: {{ app.healthChecks.period_seconds }}
          timeoutSeconds: {{ app.healthChecks.timeout_seconds }}
          failureThreshold: {{ app.healthChecks.failure_threshold }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      automountServiceAccountToken: false
"""

        service_template = """
apiVersion: v1
kind: Service
metadata:
  name: {{ app.name }}
  namespace: {{ namespace }}
  labels: {{ app.name | generate_labels(environment) | to_yaml | indent(4) }}
  annotations:
    cloud.google.com/neg: '{"ingress": true}'
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: {{ app.port }}
    protocol: TCP
    name: http
  selector: {{ app.name | selector_labels | to_yaml | indent(4) }}
"""

        hpa_template = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ app.name }}-hpa
  namespace: {{ namespace }}
  labels: {{ app.name | generate_labels(environment) | to_yaml | indent(4) }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ app.name }}
  minReplicas: {{ app.scaling.min_replicas }}
  maxReplicas: {{ app.scaling.max_replicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ app.scaling.target_cpu_utilization }}
  {% if app.scaling.target_memory_utilization %}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {{ app.scaling.target_memory_utilization }}
  {% endif %}
  behavior:
    scaleUp:
      stabilizationWindowSeconds: {{ app.scaling.scale_up_stabilization }}
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: {{ app.scaling.scale_down_stabilization }}
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
"""

        ingress_template = """
{% if app.ingress.enabled %}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ app.name }}-ingress
  namespace: {{ namespace }}
  labels: {{ app.name | generate_labels(environment) | to_yaml | indent(4) }}
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "{{ app.name }}-ip"
    {% if app.ingress.tls %}
    networking.gke.io/managed-certificates: "{{ app.name }}-cert"
    {% endif %}
    ingress.gcp.kubernetes.io/frontend-config: "{{ app.name }}-frontend-config"
spec:
  {% if app.ingress.tls and app.ingress.domain %}
  tls:
  - hosts:
    - {{ app.ingress.domain }}
    secretName: {{ app.name }}-tls
  {% endif %}
  rules:
  - host: {{ app.ingress.domain }}
    http:
      paths:
      - path: {{ app.ingress.path }}
        pathType: {{ app.ingress.path_type }}
        backend:
          service:
            name: {{ app.name }}
            port:
              number: 80
---
{% if app.ingress.tls %}
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: {{ app.name }}-cert
  namespace: {{ namespace }}
spec:
  domains:
  - {{ app.ingress.domain }}
---
{% endif %}
apiVersion: networking.gke.io/v1beta1
kind: FrontendConfig
metadata:
  name: {{ app.name }}-frontend-config
  namespace: {{ namespace }}
spec:
  redirectToHttps:
    enabled: {{ app.ingress.tls | lower }}
  sslPolicy: "gke-autopilot-ssl-policy"
{% endif %}
"""

        networkpolicy_template = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ app.name }}-netpol
  namespace: {{ namespace }}
  labels: {{ app.name | generate_labels(environment) | to_yaml | indent(4) }}
spec:
  podSelector:
    matchLabels: {{ app.name | selector_labels | to_yaml | indent(6) }}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: {{ namespace }}
    - podSelector: {}
    ports:
    - protocol: TCP
      port: {{ app.port }}
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
"""

        return {
            'deployment': deployment_template,
            'service': service_template,
            'hpa': hpa_template,
            'ingress': ingress_template,
            'networkpolicy': networkpolicy_template
        }
    
    def generate_manifests(self, context: TemplateContext) -> List[Dict[str, Any]]:
        """
        Generate complete set of Kubernetes manifests for application.
        
        Args:
            context: Template rendering context
            
        Returns:
            List of Kubernetes manifest dictionaries
        """
        logger.info(f"Generating manifests for application: {context.app_config.name}")
        
        manifests = []
        template_context = context.to_dict()
        
        try:
            # Generate deployment
            deployment_yaml = self.render_template('deployment', template_context)
            deployment_manifest = yaml.safe_load(deployment_yaml)
            manifests.append(deployment_manifest)
            
            # Generate service
            service_yaml = self.render_template('service', template_context)
            service_manifest = yaml.safe_load(service_yaml)
            manifests.append(service_manifest)
            
            # Generate HPA if scaling is configured
            if context.app_config.scaling_config.max_replicas > context.app_config.scaling_config.min_replicas:
                hpa_yaml = self.render_template('hpa', template_context)
                hpa_manifest = yaml.safe_load(hpa_yaml)
                manifests.append(hpa_manifest)
            
            # Generate ingress if enabled
            if context.app_config.ingress_config.enabled:
                ingress_yaml = self.render_template('ingress', template_context)
                # Handle multiple documents in ingress template
                for doc in yaml.safe_load_all(ingress_yaml):
                    if doc:  # Skip empty documents
                        manifests.append(doc)
            
            # Generate network policy for security
            if context.cluster_config and context.cluster_config.security_config.enable_network_policy:
                netpol_yaml = self.render_template('networkpolicy', template_context)
                netpol_manifest = yaml.safe_load(netpol_yaml)
                manifests.append(netpol_manifest)
            
            logger.info(f"Generated {len(manifests)} manifests for {context.app_config.name}")
            return manifests
            
        except Exception as e:
            logger.error(f"Failed to generate manifests: {e}")
            raise TemplateError(f"Manifest generation failed: {e}")
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a specific template with given context.
        
        Args:
            template_name: Name of template to render
            context: Template context variables
            
        Returns:
            Rendered template content
        """
        try:
            # Try to load custom template first
            if self.template_dir:
                template_path = self.template_dir / f"{template_name}.yaml"
                if template_path.exists():
                    template = self.jinja_env.get_template(f"{template_name}.yaml")
                    return template.render(**context)
            
            # Fall back to built-in template
            if template_name in self._builtin_templates:
                template = self.jinja_env.from_string(self._builtin_templates[template_name])
                return template.render(**context)
            
            raise TemplateError(f"Template not found: {template_name}")
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise TemplateError(f"Template rendering failed: {e}")
    
    def validate_manifest(self, manifest: Dict[str, Any]) -> List[str]:
        """
        Validate Kubernetes manifest for common issues.
        
        Args:
            manifest: Kubernetes manifest dictionary
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check required fields
        if 'apiVersion' not in manifest:
            warnings.append("Missing required field: apiVersion")
        
        if 'kind' not in manifest:
            warnings.append("Missing required field: kind")
        
        if 'metadata' not in manifest:
            warnings.append("Missing required field: metadata")
        elif 'name' not in manifest['metadata']:
            warnings.append("Missing required field: metadata.name")
        
        # Deployment-specific validations
        if manifest.get('kind') == 'Deployment':
            spec = manifest.get('spec', {})
            
            if 'selector' not in spec:
                warnings.append("Deployment missing selector")
            
            if 'template' not in spec:
                warnings.append("Deployment missing pod template")
            
            # Check resource requests
            containers = spec.get('template', {}).get('spec', {}).get('containers', [])
            for container in containers:
                resources = container.get('resources', {})
                requests = resources.get('requests', {})
                
                if not requests.get('cpu'):
                    warnings.append(f"Container {container.get('name', 'unknown')} missing CPU request")
                
                if not requests.get('memory'):
                    warnings.append(f"Container {container.get('name', 'unknown')} missing memory request")
        
        # Service-specific validations
        if manifest.get('kind') == 'Service':
            spec = manifest.get('spec', {})
            
            if 'selector' not in spec:
                warnings.append("Service missing selector")
            
            if not spec.get('ports'):
                warnings.append("Service missing ports configuration")
        
        # Ingress-specific validations
        if manifest.get('kind') == 'Ingress':
            spec = manifest.get('spec', {})
            
            if not spec.get('rules'):
                warnings.append("Ingress missing rules")
        
        return warnings
    
    def optimize_for_autopilot(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize manifest for GKE Autopilot best practices.
        
        Args:
            manifest: Original Kubernetes manifest
            
        Returns:
            Optimized manifest
        """
        optimized = manifest.copy()
        
        # Deployment optimizations
        if manifest.get('kind') == 'Deployment':
            spec = optimized.setdefault('spec', {})
            template_spec = spec.setdefault('template', {}).setdefault('spec', {})
            
            # Add security context
            if 'securityContext' not in template_spec:
                template_spec['securityContext'] = {
                    'runAsNonRoot': True,
                    'runAsUser': 1000,
                    'fsGroup': 2000
                }
            
            # Optimize container resources
            containers = template_spec.setdefault('containers', [])
            for container in containers:
                resources = container.setdefault('resources', {})
                requests = resources.setdefault('requests', {})
                
                # Ensure minimum CPU for Autopilot
                cpu = requests.get('cpu', '100m')
                if cpu.endswith('m') and int(cpu[:-1]) < 250:
                    requests['cpu'] = '250m'
                
                # Ensure minimum memory for Autopilot
                memory = requests.get('memory', '256Mi')
                if memory.endswith('Mi') and int(memory[:-2]) < 512:
                    requests['memory'] = '512Mi'
                
                # Set limits equal to requests for Autopilot
                resources['limits'] = requests.copy()
            
            # Add Autopilot annotations
            annotations = optimized.setdefault('metadata', {}).setdefault('annotations', {})
            annotations['gke-autopilot.io/resource-adjustment'] = 'true'
        
        # Service optimizations
        if manifest.get('kind') == 'Service':
            # Add NEG annotation for ingress
            annotations = optimized.setdefault('metadata', {}).setdefault('annotations', {})
            annotations['cloud.google.com/neg'] = '{"ingress": true}'
        
        # Ingress optimizations
        if manifest.get('kind') == 'Ingress':
            annotations = optimized.setdefault('metadata', {}).setdefault('annotations', {})
            
            # Use GCE ingress class
            annotations['kubernetes.io/ingress.class'] = 'gce'
            
            # Add frontend config for HTTPS redirect
            if 'networking.gke.io/managed-certificates' in annotations:
                annotations['ingress.gcp.kubernetes.io/frontend-config'] = f"{manifest['metadata']['name']}-frontend-config"
        
        return optimized
    
    def save_manifests(self, manifests: List[Dict[str, Any]], output_dir: Union[str, Path]) -> List[Path]:
        """
        Save manifests to YAML files.
        
        Args:
            manifests: List of Kubernetes manifests
            output_dir: Output directory for manifest files
            
        Returns:
            List of created file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        for i, manifest in enumerate(manifests):
            kind = manifest.get('kind', 'unknown').lower()
            name = manifest.get('metadata', {}).get('name', f'resource-{i}')
            
            filename = f"{name}-{kind}.yaml"
            file_path = output_path / filename
            
            with open(file_path, 'w') as f:
                yaml.dump(manifest, f, default_flow_style=False, indent=2)
            
            created_files.append(file_path)
            logger.info(f"Saved manifest: {file_path}")
        
        return created_files
    
    def create_kustomization(self, manifest_files: List[Path], output_dir: Union[str, Path]) -> Path:
        """
        Create Kustomization file for manifest management.
        
        Args:
            manifest_files: List of manifest file paths
            output_dir: Output directory
            
        Returns:
            Path to created kustomization.yaml file
        """
        output_path = Path(output_dir)
        
        kustomization = {
            'apiVersion': 'kustomize.config.k8s.io/v1beta1',
            'kind': 'Kustomization',
            'resources': [f.name for f in manifest_files],
            'commonLabels': {
                'app.kubernetes.io/managed-by': 'gke-autopilot-framework'
            }
        }
        
        kustomization_path = output_path / 'kustomization.yaml'
        with open(kustomization_path, 'w') as f:
            yaml.dump(kustomization, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created kustomization file: {kustomization_path}")
        return kustomization_path
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates"""
        templates = list(self._builtin_templates.keys())
        
        # Add custom templates if template directory exists
        if self.template_dir and self.template_dir.exists():
            for template_file in self.template_dir.glob('*.yaml'):
                template_name = template_file.stem
                if template_name not in templates:
                    templates.append(template_name)
        
        return sorted(templates)
    
    def create_custom_template(self, template_name: str, template_content: str) -> Path:
        """
        Create a custom template file.
        
        Args:
            template_name: Name of the template
            template_content: Template content (Jinja2 + YAML)
            
        Returns:
            Path to created template file
        """
        if not self.template_dir:
            raise ValueError("Template directory not configured")
        
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        template_path = self.template_dir / f"{template_name}.yaml"
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        logger.info(f"Created custom template: {template_path}")
        return template_path