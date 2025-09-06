#!/bin/bash
# 🧬 Beast Mode Deployment Validation
# Systematic testing of GKE Autopilot deployment

set -e

NAMESPACE="hackathon-app"
APP_NAME="systematic-app"

echo "🧬 Beast Mode Deployment Validation"
echo "=================================="

# Test 1: Namespace exists
echo "📋 Test 1: Namespace validation"
if kubectl get namespace $NAMESPACE &>/dev/null; then
    echo "✅ Namespace $NAMESPACE exists"
else
    echo "❌ Namespace $NAMESPACE not found"
    exit 1
fi

# Test 2: Deployment is ready
echo "📋 Test 2: Deployment validation"
kubectl wait --for=condition=available --timeout=300s deployment/$APP_NAME -n $NAMESPACE
echo "✅ Deployment $APP_NAME is ready"

# Test 3: Pods are running
echo "📋 Test 3: Pod validation"
RUNNING_PODS=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --field-selector=status.phase=Running --no-headers | wc -l)
if [ $RUNNING_PODS -gt 0 ]; then
    echo "✅ $RUNNING_PODS pods running"
else
    echo "❌ No running pods found"
    exit 1
fi

# Test 4: Service is accessible
echo "📋 Test 4: Service validation"
SERVICE_IP=$(kubectl get service systematic-app-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [ -n "$SERVICE_IP" ]; then
    echo "✅ LoadBalancer IP: $SERVICE_IP"
    
    # Test HTTP connectivity
    if curl -s --max-time 10 http://$SERVICE_IP/ >/dev/null; then
        echo "✅ HTTP connectivity confirmed"
    else
        echo "⚠️  LoadBalancer IP assigned but not yet accessible (may take a few minutes)"
    fi
else
    echo "⚠️  LoadBalancer IP not yet assigned (this is normal, takes 2-3 minutes)"
fi

# Test 5: HPA is configured
echo "📋 Test 5: Auto-scaling validation"
if kubectl get hpa systematic-app-hpa -n $NAMESPACE &>/dev/null; then
    echo "✅ HorizontalPodAutoscaler configured"
    kubectl get hpa systematic-app-hpa -n $NAMESPACE
else
    echo "❌ HorizontalPodAutoscaler not found"
fi

# Test 6: Network policy exists
echo "📋 Test 6: Security validation"
if kubectl get networkpolicy systematic-app-netpol -n $NAMESPACE &>/dev/null; then
    echo "✅ NetworkPolicy configured"
else
    echo "❌ NetworkPolicy not found"
fi

echo ""
echo "🎉 Systematic Validation Complete!"
echo ""
echo "📊 Deployment Summary:"
kubectl get pods,services,hpa -n $NAMESPACE
echo ""
echo "🔗 Useful Commands:"
echo "kubectl logs -f deployment/$APP_NAME -n $NAMESPACE"
echo "kubectl describe hpa systematic-app-hpa -n $NAMESPACE"
echo "kubectl top pods -n $NAMESPACE"