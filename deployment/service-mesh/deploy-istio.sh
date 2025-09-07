#!/bin/bash
# 🚀 GKE with Istio Service Mesh Deployment
# Demonstrates modern microservices architecture with advanced traffic management

set -e

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null || echo "your-project-id")}
CLUSTER_NAME=${2:-"hackathon-service-mesh"}
REGION=${3:-"us-central1"}
IMAGE_NAME=${4:-"gke-autopilot-ai"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🕸️  GKE with Istio Service Mesh Deployment${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
echo -e "Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "Region: ${GREEN}$REGION${NC}"
echo -e "Features: ${GREEN}Traffic management, mTLS, observability${NC}"
echo ""

# Validation
echo -e "${YELLOW}📋 Phase 1: Prerequisites Check${NC}"
if [[ "$PROJECT_ID" == "your-project-id" ]]; then
    echo -e "${RED}❌ Please provide PROJECT_ID: ./deploy-istio.sh YOUR_PROJECT_ID${NC}"
    exit 1
fi

# Enable APIs
echo -e "${YELLOW}📋 Phase 2: API Enablement${NC}"
gcloud services enable container.googleapis.com --project=$PROJECT_ID
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
gcloud services enable mesh.googleapis.com --project=$PROJECT_ID
echo -e "${GREEN}✅ APIs enabled${NC}"

# Create GKE cluster with Istio
echo -e "${YELLOW}📋 Phase 3: Creating GKE Cluster with Istio${NC}"
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo -e "${BLUE}🏗️  Creating GKE cluster with Istio support...${NC}"
    gcloud container clusters create $CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --machine-type=e2-standard-4 \
        --num-nodes=2 \
        --min-nodes=2 \
        --max-nodes=6 \
        --enable-autoscaling \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-network-policy \
        --enable-ip-alias \
        --workload-pool=$PROJECT_ID.svc.id.goog \
        --addons=Istio \
        --istio-config=auth=MTLS_PERMISSIVE \
        --release-channel=regular
else
    echo -e "${YELLOW}⚠️  Cluster already exists${NC}"
fi

# Get credentials
echo -e "${YELLOW}📋 Phase 4: Cluster Authentication${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID
echo -e "${GREEN}✅ Cluster credentials configured${NC}"

# Verify Istio installation
echo -e "${YELLOW}📋 Phase 5: Verifying Istio Installation${NC}"
kubectl get pods -n istio-system
echo -e "${GREEN}✅ Istio system verified${NC}"

# Create namespace with Istio injection
echo -e "${YELLOW}📋 Phase 6: Setting up Service Mesh Namespace${NC}"
kubectl create namespace microservices || echo "Namespace may already exist"
kubectl label namespace microservices istio-injection=enabled --overwrite
echo -e "${GREEN}✅ Namespace configured for Istio injection${NC}"

# Deploy AI Gateway (v1 and v2 for canary deployment)
echo -e "${YELLOW}📋 Phase 7: Deploying AI Gateway (Multi-Version)${NC}"

cat <<EOF | kubectl apply -f -
# AI Gateway v1
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-gateway-v1
  namespace: microservices
  labels:
    app: ai-gateway
    version: v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-gateway
      version: v1
  template:
    metadata:
      labels:
        app: ai-gateway
        version: v1
    spec:
      containers:
      - name: gateway
        image: gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
        ports:
        - containerPort: 8080
        env:
        - name: SERVICE_VERSION
          value: "v1"
        - name: SERVICE_NAME
          value: "ai-gateway"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
# AI Gateway v2 (new version for canary)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-gateway-v2
  namespace: microservices
  labels:
    app: ai-gateway
    version: v2
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-gateway
      version: v2
  template:
    metadata:
      labels:
        app: ai-gateway
        version: v2
    spec:
      containers:
      - name: gateway
        image: gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
        ports:
        - containerPort: 8080
        env:
        - name: SERVICE_VERSION
          value: "v2"
        - name: SERVICE_NAME
          value: "ai-gateway"
        - name: FEATURE_FLAG_NEW_AI
          value: "true"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
# AI Processor Service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-processor
  namespace: microservices
  labels:
    app: ai-processor
    version: v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-processor
      version: v1
  template:
    metadata:
      labels:
        app: ai-processor
        version: v1
    spec:
      containers:
      - name: processor
        image: gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
        ports:
        - containerPort: 8080
        env:
        - name: SERVICE_VERSION
          value: "v1"
        - name: SERVICE_NAME
          value: "ai-processor"
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "400m"
EOF

# Create Kubernetes services
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: ai-gateway
  namespace: microservices
  labels:
    app: ai-gateway
spec:
  ports:
  - port: 80
    targetPort: 8080
    name: http
  selector:
    app: ai-gateway
---
apiVersion: v1
kind: Service
metadata:
  name: ai-processor
  namespace: microservices
  labels:
    app: ai-processor
spec:
  ports:
  - port: 80
    targetPort: 8080
    name: http
  selector:
    app: ai-processor
EOF

echo -e "${GREEN}✅ Microservices deployed${NC}"

# Configure Istio traffic management
echo -e "${YELLOW}📋 Phase 8: Configuring Istio Traffic Management${NC}"

# Virtual Service for canary deployment (90% v1, 10% v2)
cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ai-gateway
  namespace: microservices
spec:
  hosts:
  - ai-gateway
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: ai-gateway
        subset: v2
  - route:
    - destination:
        host: ai-gateway
        subset: v1
      weight: 90
    - destination:
        host: ai-gateway
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: ai-gateway
  namespace: microservices
spec:
  host: ai-gateway
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
# Circuit breaker for AI processor
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: ai-processor
  namespace: microservices
spec:
  host: ai-processor
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    connectionPool:
      tcp:
        maxConnections: 10
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 30s
EOF

# Create Gateway for external access
cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: ai-gateway
  namespace: microservices
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ai-gateway-external
  namespace: microservices
spec:
  hosts:
  - "*"
  gateways:
  - ai-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: ai-gateway
        port:
          number: 80
EOF

echo -e "${GREEN}✅ Istio traffic management configured${NC}"

# Wait for deployments
echo -e "${YELLOW}📋 Phase 9: Waiting for Deployments${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/ai-gateway-v1 -n microservices
kubectl wait --for=condition=available --timeout=300s deployment/ai-gateway-v2 -n microservices
kubectl wait --for=condition=available --timeout=300s deployment/ai-processor -n microservices
echo -e "${GREEN}✅ All deployments ready${NC}"

# Get Istio ingress gateway IP
echo -e "${YELLOW}📋 Phase 10: Getting Service Information${NC}"
INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo ""
echo -e "${GREEN}🎉 Istio Service Mesh Deployment Complete!${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""
echo -e "${BLUE}🕸️  Service Mesh Features:${NC}"
echo -e "  ✅ Automatic sidecar injection"
echo -e "  ✅ mTLS between services"
echo -e "  ✅ Canary deployment (90% v1, 10% v2)"
echo -e "  ✅ Circuit breaker on AI processor"
echo -e "  ✅ Traffic management and routing"
echo ""
echo -e "${BLUE}🌐 Access Information:${NC}"
if [[ -n "$INGRESS_IP" ]]; then
    echo -e "Ingress IP: ${GREEN}$INGRESS_IP${NC}"
    echo ""
    echo -e "${BLUE}🧪 Test the service mesh:${NC}"
    echo "# Normal traffic (90% v1, 10% v2):"
    echo "curl http://$INGRESS_IP/"
    echo ""
    echo "# Force canary version:"
    echo "curl -H 'canary: true' http://$INGRESS_IP/"
else
    echo -e "Ingress IP: ${YELLOW}Pending (check with: kubectl get svc istio-ingressgateway -n istio-system)${NC}"
fi
echo ""
echo -e "${BLUE}📊 Monitor service mesh:${NC}"
echo "kubectl get pods -n microservices"
echo "kubectl get virtualservices -n microservices"
echo "kubectl get destinationrules -n microservices"
echo ""
echo -e "${BLUE}🔍 Istio observability:${NC}"
echo "kubectl port-forward -n istio-system svc/kiali 20001:20001"
echo "kubectl port-forward -n istio-system svc/grafana 3000:3000"
echo ""
echo -e "${GREEN}🚀 This demonstrates advanced microservices architecture for the hackathon!${NC}"