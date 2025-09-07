#!/bin/bash
# 🚀 GKE Autopilot AI Microservice Deployment
# Hackathon-ready deployment with real AI capabilities
# Demonstrates systematic PDCA methodology

set -e

# Source PDCA framework
source "$(dirname "$0")/../../scripts/pdca-framework.sh" 2>/dev/null || echo "PDCA framework not available"

# Configuration with sensible defaults
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null || echo "your-project-id")}
CLUSTER_NAME=${2:-"hackathon-autopilot"}
REGION=${3:-"us-central1"}
IMAGE_NAME=${4:-"gke-autopilot-ai"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GKE Autopilot AI Microservice Deployment${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
echo -e "Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "Region: ${GREEN}$REGION${NC}"
echo -e "Image: ${GREEN}$IMAGE_NAME${NC}"
echo ""

# PDCA PLAN Phase
pdca_plan "GKE Autopilot AI Microservice Deployment" 2>/dev/null || echo -e "${YELLOW}📋 PLAN: Prerequisites and Validation${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Install: https://kubernetes.io/docs/tasks/tools/${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Install: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if [[ "$PROJECT_ID" == "your-project-id" ]]; then
    echo -e "${RED}❌ Please provide PROJECT_ID: ./deploy.sh YOUR_PROJECT_ID${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites validated${NC}"

# Enable required APIs
echo -e "${YELLOW}📋 Phase 2: API Enablement${NC}"
gcloud services enable container.googleapis.com --project=$PROJECT_ID
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
echo -e "${GREEN}✅ APIs enabled${NC}"

# PDCA DO Phase
pdca_do "Build and Deploy AI Microservice" 2>/dev/null || echo -e "${YELLOW}🔨 DO: Building AI Microservice${NC}"
cd deployment/autopilot/app

# Configure Docker for GCR
gcloud auth configure-docker --quiet

# Build the image
echo -e "${BLUE}🏗️  Building Docker image...${NC}"
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:latest .

# Push to Google Container Registry
echo -e "${BLUE}📤 Pushing to Container Registry...${NC}"
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:latest

cd ../../..
echo -e "${GREEN}✅ Container image built and pushed${NC}"

# Create Autopilot cluster
echo -e "${YELLOW}📋 Phase 4: GKE Autopilot Cluster${NC}"
if gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}⚠️  Cluster $CLUSTER_NAME already exists${NC}"
else
    echo -e "${BLUE}🚀 Creating GKE Autopilot cluster (this takes ~5 minutes)...${NC}"
    gcloud container clusters create-auto $CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --release-channel=rapid \
        --enable-network-policy \
        --enable-ip-alias \
        --workload-pool=$PROJECT_ID.svc.id.goog
fi

# Get cluster credentials
echo -e "${YELLOW}📋 Phase 5: Cluster Authentication${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID
echo -e "${GREEN}✅ Cluster credentials configured${NC}"

# Update manifests with project ID
echo -e "${YELLOW}📋 Phase 6: Preparing Manifests${NC}"
# Create temporary manifests with correct project ID
mkdir -p /tmp/autopilot-manifests
cp deployment/autopilot/manifests/* /tmp/autopilot-manifests/
sed -i "s/PROJECT_ID/$PROJECT_ID/g" /tmp/autopilot-manifests/deployment.yaml
echo -e "${GREEN}✅ Manifests prepared${NC}"

# Deploy application
echo -e "${YELLOW}📋 Phase 7: Deploying AI Microservice${NC}"
kubectl apply -f /tmp/autopilot-manifests/
echo -e "${GREEN}✅ AI microservice deployed${NC}"

# PDCA CHECK Phase
pdca_check "Validate Deployment Success" 2>/dev/null || echo -e "${YELLOW}✅ CHECK: Waiting for Deployment${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/ai-microservice -n hackathon-app
echo -e "${GREEN}✅ Deployment is ready${NC}"

# Get service information
echo -e "${YELLOW}📋 Phase 9: Service Information${NC}"
kubectl get pods,services,hpa -n hackathon-app

# Get external IP (may take a few minutes)
echo -e "${BLUE}🌐 Getting external IP (this may take a few minutes)...${NC}"
EXTERNAL_IP=""
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get service ai-microservice -n hackathon-app -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [[ -n "$EXTERNAL_IP" ]]; then
        break
    fi
    echo -e "${YELLOW}⏳ Waiting for external IP... (attempt $i/30)${NC}"
    sleep 10
done

# Clean up temp files
rm -rf /tmp/autopilot-manifests

echo ""
echo -e "${GREEN}🎉 GKE Autopilot Deployment Complete!${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "Namespace: ${GREEN}hackathon-app${NC}"
echo -e "Image: ${GREEN}gcr.io/$PROJECT_ID/$IMAGE_NAME:latest${NC}"

if [[ -n "$EXTERNAL_IP" ]]; then
    echo -e "External IP: ${GREEN}$EXTERNAL_IP${NC}"
    echo ""
    echo -e "${BLUE}🧪 Test your AI microservice:${NC}"
    echo "curl http://$EXTERNAL_IP/health"
    echo "curl http://$EXTERNAL_IP/demo"
    echo "curl -X POST http://$EXTERNAL_IP/ai/process -H 'Content-Type: application/json' -d '{\"task\":\"analyze data\"}'"
else
    echo -e "External IP: ${YELLOW}Pending (check with: kubectl get services -n hackathon-app)${NC}"
fi

echo ""
echo -e "${BLUE}📊 Useful commands:${NC}"
echo "kubectl get pods -n hackathon-app"
echo "kubectl logs -f deployment/ai-microservice -n hackathon-app"
echo "kubectl describe hpa ai-microservice-hpa -n hackathon-app"
echo ""
echo -e "${BLUE}📈 Monitor your cluster:${NC}"
echo "https://console.cloud.google.com/kubernetes/clusters/details/$REGION/$CLUSTER_NAME/details?project=$PROJECT_ID"
echo ""
echo -e "${BLUE}💰 Cost monitoring:${NC}"
echo "https://console.cloud.google.com/billing/reports?project=$PROJECT_ID"
echo ""
echo -e "${GREEN}🚀 Your AI microservice is now running on GKE Autopilot!${NC}"