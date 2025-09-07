#!/bin/bash
# 🚀 GKE Cost-Optimized Deployment with Spot Instances
# Demonstrates cost consciousness with fault-tolerant architecture

set -e

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null || echo "your-project-id")}
CLUSTER_NAME=${2:-"hackathon-cost-optimized"}
REGION=${3:-"us-central1"}
IMAGE_NAME=${4:-"gke-autopilot-ai"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 GKE Cost-Optimized Deployment (Spot Instances)${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
echo -e "Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "Region: ${GREEN}$REGION${NC}"
echo -e "Strategy: ${GREEN}Mixed node pools (regular + spot)${NC}"
echo ""

# Validation
echo -e "${YELLOW}📋 Phase 1: Prerequisites Check${NC}"
if [[ "$PROJECT_ID" == "your-project-id" ]]; then
    echo -e "${RED}❌ Please provide PROJECT_ID: ./deploy-spot.sh YOUR_PROJECT_ID${NC}"
    exit 1
fi

# Enable APIs
echo -e "${YELLOW}📋 Phase 2: API Enablement${NC}"
gcloud services enable container.googleapis.com --project=$PROJECT_ID
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
echo -e "${GREEN}✅ APIs enabled${NC}"

# Create cost-optimized GKE cluster
echo -e "${YELLOW}📋 Phase 3: Creating Cost-Optimized Cluster${NC}"
if gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}⚠️  Cluster $CLUSTER_NAME already exists${NC}"
else
    echo -e "${BLUE}🏗️  Creating GKE cluster with mixed node pools...${NC}"
    
    # Create cluster with regular node pool
    gcloud container clusters create $CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --machine-type=e2-standard-2 \
        --num-nodes=1 \
        --min-nodes=1 \
        --max-nodes=3 \
        --enable-autoscaling \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-network-policy \
        --enable-ip-alias \
        --workload-pool=$PROJECT_ID.svc.id.goog \
        --node-labels=workload-type=critical \
        --release-channel=regular
    
    # Add spot instance node pool
    echo -e "${BLUE}💰 Adding spot instance node pool for cost optimization...${NC}"
    gcloud container node-pools create spot-pool \
        --cluster=$CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --machine-type=e2-standard-4 \
        --spot \
        --num-nodes=0 \
        --min-nodes=0 \
        --max-nodes=10 \
        --enable-autoscaling \
        --enable-autorepair \
        --enable-autoupgrade \
        --node-labels=workload-type=batch,cost-optimized=true \
        --node-taints=spot=true:NoSchedule
fi

# Get credentials
echo -e "${YELLOW}📋 Phase 4: Cluster Authentication${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID
echo -e "${GREEN}✅ Cluster credentials configured${NC}"

# Deploy cost-optimized workloads
echo -e "${YELLOW}📋 Phase 5: Deploying Cost-Optimized Workloads${NC}"

# Create namespace
kubectl create namespace cost-optimized || echo "Namespace may already exist"

# Deploy critical workload (regular nodes)
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-api
  namespace: cost-optimized
  labels:
    app: critical-api
    workload-type: critical
spec:
  replicas: 2
  selector:
    matchLabels:
      app: critical-api
  template:
    metadata:
      labels:
        app: critical-api
        workload-type: critical
    spec:
      nodeSelector:
        workload-type: critical
      containers:
      - name: api
        image: gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        env:
        - name: WORKLOAD_TYPE
          value: "critical"
---
apiVersion: v1
kind: Service
metadata:
  name: critical-api
  namespace: cost-optimized
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: critical-api
EOF

# Deploy batch workload (spot nodes)
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-processor
  namespace: cost-optimized
  labels:
    app: batch-processor
    workload-type: batch
spec:
  replicas: 3
  selector:
    matchLabels:
      app: batch-processor
  template:
    metadata:
      labels:
        app: batch-processor
        workload-type: batch
    spec:
      nodeSelector:
        cost-optimized: "true"
      tolerations:
      - key: spot
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: processor
        image: gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: WORKLOAD_TYPE
          value: "batch"
        - name: SPOT_INSTANCE
          value: "true"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: batch-processor-hpa
  namespace: cost-optimized
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: batch-processor
  minReplicas: 1
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
EOF

echo -e "${GREEN}✅ Cost-optimized workloads deployed${NC}"

# Wait for deployments
echo -e "${YELLOW}📋 Phase 6: Waiting for Deployments${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/critical-api -n cost-optimized
echo -e "${GREEN}✅ Critical API ready${NC}"

# Show cost optimization info
echo -e "${YELLOW}📋 Phase 7: Cost Optimization Summary${NC}"
kubectl get nodes -o wide
kubectl get pods -n cost-optimized -o wide

echo ""
echo -e "${GREEN}🎉 Cost-Optimized GKE Deployment Complete!${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""
echo -e "${BLUE}💰 Cost Optimization Features:${NC}"
echo -e "  ✅ Spot instances for batch workloads (up to 80% cost savings)"
echo -e "  ✅ Regular instances for critical workloads (guaranteed availability)"
echo -e "  ✅ Auto-scaling based on workload type"
echo -e "  ✅ Proper node taints and tolerations"
echo ""
echo -e "${BLUE}🏗️  Architecture:${NC}"
echo -e "  • Critical API: Regular nodes (high availability)"
echo -e "  • Batch Processor: Spot nodes (cost optimized)"
echo -e "  • Auto-scaling: 1-20 replicas based on demand"
echo ""
echo -e "${BLUE}📊 Monitor costs:${NC}"
echo "kubectl top nodes"
echo "kubectl describe nodes | grep -A5 'Spot:'"
echo ""
echo -e "${BLUE}🧪 Test workload placement:${NC}"
echo "kubectl get pods -n cost-optimized -o wide"
echo ""
echo -e "${GREEN}💡 This demonstrates cost-conscious architecture for the hackathon!${NC}"