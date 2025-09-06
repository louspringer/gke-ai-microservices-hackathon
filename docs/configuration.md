# Configuration Management

GKE Local uses YAML-based configuration files to manage all aspects of the local development environment. This document describes the configuration system and available options.

## Configuration Files

### Base Configuration

The main configuration file is `gke-local.yaml` in your project root. This file contains all the default settings for your local development environment.

### Environment-Specific Overrides

You can create environment-specific configuration files using the pattern `gke-local.{environment}.yaml`:

- `gke-local.local.yaml` - Local development overrides
- `gke-local.staging.yaml` - Staging environment settings  
- `gke-local.production.yaml` - Production deployment settings

Environment-specific files override values from the base configuration.

## Configuration Structure

### Project Settings

```yaml
project_name: "my-gke-local-project"  # Must be alphanumeric with hyphens/underscores
environment: "local"                   # Environment name
log_level: "info"                     # debug, info, warning, error
```

### Cluster Configuration

```yaml
cluster:
  name: "local-gke-dev"               # Cluster name
  kubernetes_version: "1.28"          # Kubernetes version (X.Y format)
  nodes: 3                            # Number of nodes
  registry_port: 5000                 # Local registry port
  ingress_port: 80                    # Ingress controller port
  api_server_port: 6443               # Kubernetes API server port
```

### Simulation Settings

```yaml
simulation:
  cloud_run:
    enabled: true                     # Enable Cloud Run simulation
    scale_to_zero: true               # Enable scale-to-zero behavior
    cold_start_delay: "2s"            # Cold start delay simulation
    max_instances: 100                # Maximum instances
    concurrency: 80                   # Requests per instance
    timeout: "300s"                   # Request timeout
  
  autopilot:
    enabled: true                     # Enable Autopilot simulation
    node_auto_provisioning: true      # Simulate node provisioning
    resource_optimization: true       # Enable resource optimization
    security_policies: true           # Enforce security policies
    intelligent_scheduling: true      # Simulate intelligent scheduling
```

### Services Configuration

```yaml
services:
  monitoring:
    prometheus: true                  # Enable Prometheus
    grafana: true                     # Enable Grafana
    jaeger: true                      # Enable Jaeger tracing
    prometheus_port: 9090             # Prometheus port
    grafana_port: 3000                # Grafana port
    jaeger_port: 16686                # Jaeger port
  
  ai:
    model_serving: true               # Enable AI model serving
    ghostbusters: true                # Enable Ghostbusters framework
    gpu_support: false                # Enable GPU support
    inference_timeout: 30             # AI inference timeout (seconds)
  
  hot_reload: true                    # Enable hot reload
  debug_proxy: true                   # Enable debug proxy
  log_aggregation: true               # Enable log aggregation
```

### Environment Variables and Secrets

```yaml
environment_vars:
  NODE_ENV: "development"
  LOG_LEVEL: "debug"
  API_BASE_URL: "http://localhost:8000"

secrets:
  DATABASE_PASSWORD: "secret-value"
  API_KEY: "your-api-key"
```

### File Watching

```yaml
watch_paths:
  - "./src"
  - "./services"
  - "./configs"

ignore_patterns:
  - "*.pyc"
  - "__pycache__"
  - ".git"
  - "node_modules"
  - ".venv"
  - "*.log"
```

## CLI Configuration Commands

### View Current Configuration

```bash
gke-local config
```

### Validate Configuration

```bash
gke-local validate
```

### Use Specific Environment

```bash
gke-local config --environment staging
```

### Use Custom Config Directory

```bash
gke-local config --config-dir ./custom-configs
```

## Configuration Validation

The configuration system validates all settings and provides helpful error messages:

- **Project Name**: Must be alphanumeric with hyphens or underscores
- **Kubernetes Version**: Must be in "X.Y" format (e.g., "1.28")
- **Ports**: Must be valid port numbers (1-65535)
- **Timeouts**: Must be in format like "30s", "5m", "1h"
- **Paths**: Watch paths are validated for existence

## Environment-Specific Examples

### Local Development

```yaml
# gke-local.local.yaml
log_level: "debug"
cluster:
  nodes: 1  # Minimal resources for local dev
services:
  ai:
    gpu_support: false  # No GPU in local environment
```

### Staging Environment

```yaml
# gke-local.staging.yaml
cluster:
  nodes: 5
services:
  monitoring:
    prometheus: true
    grafana: true
environment_vars:
  NODE_ENV: "staging"
  LOG_LEVEL: "info"
```

### Production Deployment

```yaml
# gke-local.production.yaml
log_level: "warning"
cluster:
  nodes: 10
simulation:
  cloud_run:
    max_instances: 1000
  autopilot:
    resource_optimization: true
services:
  ai:
    gpu_support: true
    inference_timeout: 60
```

## Best Practices

1. **Keep Secrets Separate**: Use environment-specific files for sensitive data
2. **Validate Early**: Run `gke-local validate` before starting services
3. **Use Defaults**: Only override settings that need to be different
4. **Document Changes**: Comment your configuration files
5. **Version Control**: Include base config in git, exclude secrets