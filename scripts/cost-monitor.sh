#!/bin/bash
# 🧬 Beast Mode Cost Monitoring
# Systematic GKE Autopilot cost tracking and optimization

set -e

PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
CLUSTER_NAME=${2:-"hackathon-autopilot"}
REGION=${3:-"us-central1"}

echo "🧬 Beast Mode Cost Monitoring"
echo "============================"
echo "Project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME"
echo ""

# Resource usage summary
echo "📊 Current Resource Usage:"
echo "=========================="
kubectl top nodes 2>/dev/null || echo "⚠️  Metrics server not ready yet"
echo ""
kubectl top pods --all-namespaces 2>/dev/null || echo "⚠️  Pod metrics not ready yet"
echo ""

# Autopilot cost optimization info
echo "💰 Autopilot Cost Optimization:"
echo "==============================="
echo "✅ Pay only for requested CPU, memory, and storage"
echo "✅ No charges for system pods or unused node capacity"
echo "✅ Automatic bin packing optimizes resource utilization"
echo "✅ Preemptible nodes used when possible"
echo ""

# Resource requests summary
echo "📋 Resource Requests by Namespace:"
echo "=================================="
kubectl get pods --all-namespaces -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory" --no-headers | sort

echo ""
echo "🔗 Cost Monitoring Links:"
echo "========================="
echo "Billing Reports: https://console.cloud.google.com/billing/reports?project=$PROJECT_ID"
echo "GKE Cost Breakdown: https://console.cloud.google.com/kubernetes/clusters/details/$REGION/$CLUSTER_NAME/cost?project=$PROJECT_ID"
echo "Resource Usage: https://console.cloud.google.com/kubernetes/clusters/details/$REGION/$CLUSTER_NAME/observability/metrics?project=$PROJECT_ID"

echo ""
echo "💡 Cost Optimization Tips:"
echo "=========================="
echo "1. Right-size resource requests (CPU/memory)"
echo "2. Use HPA to scale based on actual usage"
echo "3. Set appropriate resource limits"
echo "4. Monitor and adjust based on actual usage patterns"
echo "5. Use preemptible nodes for non-critical workloads"