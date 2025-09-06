#!/bin/bash
# 🚀 Systematic GKE Autopilot Deployment Framework
# Beast Mode DNA Implementation for Hackathon Excellence

set -e

# Configuration with sensible defaults
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null || echo "your-project-id")}
CLUSTER_NAME=${2:-"hackathon-autopilot"}
REGION=${3:-"us-central1"}
APP_NAME=${4:-"systematic-app"}

# Colors for systematic output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧬 Beast Mode GKE Autopilot Deployment${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
echo -e "Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "Region: ${GREEN}$REGION${NC}"
echo -e "App: ${GREEN}$APP_NAME${NC}"
echo ""

# Systematic validation
echo -e "${YELLOW}📋 Phase 1: Systematic Validation${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Install: https://kubernetes.io/docs/tasks/tools/${NC}"
    exit 1
fi

if [[ "$PROJECT_ID" == "your-project-id" ]]; then
    echo -e "${RED}❌ Please set PROJECT_ID or configure gcloud: gcloud config set project YOUR_PROJECT${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites validated${NC}"

# Enable required APIs
echo -e "${YELLOW}📋 Phase 2: API Enablement${NC}"
gcloud services enable container.googleapis.com --project=$PROJECT_ID
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
echo -e "${GREEN}✅ APIs enabled${NC}"

# Create Autopilot cluster (serverless Kubernetes excellence)
echo -e "${YELLOW}📋 Phase 3: Autopilot Cluster Creation${NC}"
if gcloud container clusters describe $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}⚠️  Cluster $CLUSTER_NAME already exists${NC}"
else
    echo -e "${BLUE}🚀 Creating Autopilot cluster (this takes ~5 minutes)...${NC}"
    gcloud container clusters create-auto $CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --release-channel=rapid \
        --enable-network-policy \
        --enable-ip-alias
fi

# Get cluster credentials
echo -e "${YELLOW}📋 Phase 4: Cluster Authentication${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION --project=$PROJECT_ID
echo -e "${GREEN}✅ Cluster credentials configured${NC}"

# Deploy application with systematic excellence
echo -e "${YELLOW}📋 Phase 5: Application Deployment${NC}"
if [[ -d "deployment/autopilot/manifests" ]]; then
    kubectl apply -f deployment/autopilot/manifests/
    echo -e "${GREEN}✅ Application deployed${NC}"
else
    echo -e "${YELLOW}⚠️  No manifests found. Creating sample deployment...${NC}"
    kubectl create deployment $APP_NAME --image=nginx:latest
    kubectl expose deployment $APP_NAME --type=LoadBalancer --port=80
    echo -e "${GREEN}✅ Sample application deployed${NC}"
fi

# Systematic monitoring setup
echo -e "${YELLOW}📋 Phase 6: Monitoring & Observability${NC}"
kubectl get pods,services,deployments
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}📊 Access your application:${NC}"
echo "kubectl get services"
echo ""
echo -e "${BLUE}📈 Monitor your cluster:${NC}"
echo "https://console.cloud.google.com/kubernetes/clusters/details/$REGION/$CLUSTER_NAME/details?project=$PROJECT_ID"
echo ""
echo -e "${BLUE}💰 Cost monitoring:${NC}"
echo "https://console.cloud.google.com/billing/reports?project=$PROJECT_ID"