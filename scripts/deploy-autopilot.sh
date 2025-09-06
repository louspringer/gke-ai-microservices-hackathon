#!/bin/bash
# Systematic GKE Autopilot Deployment
# Beast Mode DNA: Serverless Kubernetes Excellence

set -e

PROJECT_ID=${1:-"your-project-id"}
CLUSTER_NAME=${2:-"hackathon-autopilot"}
REGION=${3:-"us-central1"}
APP_NAME=${4:-"systematic-app"}

echo "🚀 Beast Mode GKE Autopilot Deployment"
echo "======================================"
echo "Project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Application: $APP_NAME"
echo ""

# Validate prerequisites
echo "🔍 Validating prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

# Set project
echo "🔧 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable container.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create GKE Autopilot cluster (if it doesn't exist)
echo "🏗️  Creating GKE Autopilot cluster..."
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION &> /dev/null; then
    echo "Creating new Autopilot cluster: $CLUSTER_NAME"
    gcloud container clusters create-auto $CLUSTER_NAME \
        --project=$PROJECT_ID \
        --region=$REGION \
        --release-channel=rapid \
        --enable-autorepair \
        --enable-autoupgrade
    
    echo "✅ Autopilot cluster created successfully!"
else
    echo "✅ Autopilot cluster already exists"
fi

# Get cluster credentials
echo "🔑 Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Deploy application (placeholder - customize for your app)
echo "🚀 Deploying application to Autopilot..."
echo "⚠️  Customize this section for your specific application"

echo ""
echo "🎉 Beast Mode GKE Autopilot Deployment Complete!"
echo "==============================================="
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo ""
echo "🧬 Systematic excellence achieved through Beast Mode DNA!"
