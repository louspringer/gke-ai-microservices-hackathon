# Cluster Management

GKE Local uses Kind (Kubernetes in Docker) to create local Kubernetes clusters that simulate GKE Autopilot behavior. This document describes how to manage these clusters.

## Quick Start

```bash
# Create a minimal development cluster
gke-local cluster create

# Check cluster status
gke-local cluster status

# Delete the cluster
gke-local cluster delete
```

## Cluster Templates

GKE Local provides several pre-configured cluster templates optimized for different use cases:

### Minimal Template (`minimal`)
- **Use case**: Basic development and testing
- **Configuration**: Single control-plane node
- **Resources**: Minimal resource usage
- **Features**: Basic Kubernetes functionality

```bash
gke-local cluster create --template minimal
```

### AI Template (`ai`)
- **Use case**: AI/ML workload development
- **Configuration**: 1 control-plane + 2 worker nodes
- **Resources**: Optimized for AI workloads
- **Features**: GPU support, device plugins, AI-specific labels

```bash
gke-local cluster create --template ai
```

### Staging Template (`staging`)
- **Use case**: Staging environment simulation
- **Configuration**: 1 control-plane + 5 worker nodes
- **Resources**: Multi-zone simulation
- **Features**: Zone distribution, topology management

```bash
gke-local cluster create --template staging
```

### Autopilot Template (`autopilot`)
- **Use case**: GKE Autopilot behavior simulation
- **Configuration**: 1 control-plane + 2 optimized workers
- **Resources**: Resource quotas and limits
- **Features**: Security policies, admission controllers, resource optimization

```bash
gke-local cluster create --template autopilot
```

## CLI Commands

### Create Cluster

```bash
gke-local cluster create [OPTIONS]
```

**Options:**
- `--template, -t`: Cluster template (minimal, ai, staging, autopilot)
- `--wait/--no-wait`: Wait for cluster to be ready (default: true)
- `--environment, -e`: Environment configuration to use
- `--verbose, -v`: Enable verbose output

**Examples:**
```bash
# Create with AI template
gke-local cluster create --template ai

# Create without waiting
gke-local cluster create --no-wait

# Create with verbose output
gke-local cluster create --template autopilot --verbose
```

### Delete Cluster

```bash
gke-local cluster delete [OPTIONS]
```

Permanently deletes the Kind cluster and all associated resources.

**Examples:**
```bash
# Delete cluster
gke-local cluster delete

# Delete with verbose output
gke-local cluster delete --verbose
```

### Reset Cluster

```bash
gke-local cluster reset [OPTIONS]
```

Deletes the existing cluster and creates a new one with the same configuration.

**Examples:**
```bash
# Reset cluster
gke-local cluster reset

# Reset with verbose output
gke-local cluster reset --verbose
```

### Cluster Status

```bash
gke-local cluster status [OPTIONS]
```

**Options:**
- `--output, -o`: Output format (table, json)
- `--verbose, -v`: Show detailed node information

**Examples:**
```bash
# Show status in table format
gke-local cluster status

# Show status in JSON format
gke-local cluster status --output json

# Show detailed status
gke-local cluster status --verbose
```

**Sample Output:**
```
📊 Cluster Status: local-gke-dev
────────────────────────────────────────
✅ Status: Ready
🟢 Running: Yes
🖥️  Nodes: 3
🔧 Kubeconfig: /Users/user/.kube/config

📋 Node Details:
  ✅ local-gke-dev-control-plane: True
  ✅ local-gke-dev-worker: True
  ✅ local-gke-dev-worker2: True
```

### Get Kubeconfig

```bash
gke-local cluster kubeconfig [OPTIONS]
```

Outputs the kubeconfig for the cluster to stdout.

**Examples:**
```bash
# Print kubeconfig
gke-local cluster kubeconfig

# Save kubeconfig to file
gke-local cluster kubeconfig > my-kubeconfig.yaml

# Use with kubectl
export KUBECONFIG=$(gke-local cluster kubeconfig)
kubectl get nodes
```

### List Templates

```bash
gke-local cluster templates
```

Shows all available cluster templates with descriptions.

**Sample Output:**
```
📋 Available Cluster Templates:
───────────────────────────────────────
• minimal      - Single-node cluster for basic development
• ai           - Multi-node cluster optimized for AI workloads
• staging      - Multi-node cluster simulating staging environment
• autopilot    - Cluster configured to simulate GKE Autopilot

💡 Use with: gke-local cluster create --template <name>
```

### Wait for Ready

```bash
gke-local cluster wait [OPTIONS]
```

**Options:**
- `--timeout, -t`: Timeout in seconds (default: 300)

Waits for the cluster to be ready before returning.

**Examples:**
```bash
# Wait with default timeout
gke-local cluster wait

# Wait with custom timeout
gke-local cluster wait --timeout 600
```

## Cluster Configuration

Clusters are configured through the `gke-local.yaml` configuration file:

```yaml
cluster:
  name: "local-gke-dev"
  kubernetes_version: "1.28"
  nodes: 3
  registry_port: 5000
  ingress_port: 80
  api_server_port: 6443
```

### Configuration Options

- **name**: Cluster name (used as Kind cluster name)
- **kubernetes_version**: Kubernetes version to use
- **nodes**: Total number of nodes (including control plane)
- **registry_port**: Port for local container registry
- **ingress_port**: Port for ingress controller
- **api_server_port**: Kubernetes API server port

## Networking

### Port Mappings

Kind clusters expose services through port mappings:

- **Port 80**: HTTP ingress traffic
- **Port 443**: HTTPS ingress traffic  
- **Port 6443**: Kubernetes API server
- **Port 5000**: Local container registry

### CNI Plugin

Clusters use Calico CNI for:
- Network policies
- Pod-to-pod communication
- Service networking
- Ingress traffic routing

### Local Registry Integration

Clusters are automatically configured to use the local container registry:
- Registry accessible at `localhost:5000`
- No authentication required
- Automatic image pull from local registry

## Troubleshooting

### Cluster Won't Start

```bash
# Check Docker is running
docker ps

# Check Kind installation
kind version

# Reset cluster
gke-local cluster reset

# Check logs
kubectl logs -n kube-system -l component=kube-apiserver
```

### Network Issues

```bash
# Check CNI pods
kubectl get pods -n kube-system -l k8s-app=calico-node

# Restart CNI
kubectl delete pods -n kube-system -l k8s-app=calico-node

# Check ingress controller
kubectl get pods -n ingress-nginx
```

### Resource Issues

```bash
# Check node resources
kubectl describe nodes

# Check resource quotas
kubectl get resourcequotas --all-namespaces

# Free up resources
docker system prune
```

### Port Conflicts

If ports are already in use:

1. **Change ports in configuration:**
   ```yaml
   cluster:
     ingress_port: 8080
     api_server_port: 6444
     registry_port: 5001
   ```

2. **Find conflicting processes:**
   ```bash
   lsof -i :80
   lsof -i :6443
   ```

3. **Reset cluster with new configuration:**
   ```bash
   gke-local cluster reset
   ```

## Advanced Usage

### Custom Templates

You can create custom cluster configurations by extending the base templates:

```python
from gke_local.cluster.templates import ClusterTemplates

# Get base template
config = ClusterTemplates.get_template('ai')

# Customize
config['nodes'].append({
    'role': 'worker',
    'labels': {'custom': 'true'}
})

# Use with KindManager
manager = KindManager(your_config)
# ... use custom config
```

### Event Handling

Monitor cluster lifecycle events:

```python
from gke_local.cluster.lifecycle import ClusterLifecycleManager

manager = ClusterLifecycleManager(config)

def on_ready(event):
    print(f"Cluster {event.cluster_name} is ready!")

manager.add_event_handler('cluster_ready', on_ready)
await manager.create_and_start()
```

### Multiple Clusters

Manage multiple clusters simultaneously:

```python
from gke_local.cluster.lifecycle import ClusterOrchestrator

orchestrator = ClusterOrchestrator()

# Add clusters
orchestrator.add_cluster(dev_config)
orchestrator.add_cluster(staging_config)

# Start all
results = await orchestrator.start_all()
```

## Best Practices

1. **Use appropriate templates** for your use case
2. **Monitor resource usage** to avoid system overload
3. **Reset clusters regularly** to ensure clean state
4. **Use verbose output** when troubleshooting
5. **Check cluster status** before deploying services
6. **Keep clusters small** for development (1-3 nodes)
7. **Use staging template** for integration testing
8. **Clean up unused clusters** to free resources