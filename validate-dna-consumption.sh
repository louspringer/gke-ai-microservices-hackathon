#!/bin/bash
# Beast Mode DNA Consumption Validation Script
# Run this in the fresh Kiro instance to validate spore assimilation

echo "🧬 Beast Mode DNA Consumption Validation"
echo "========================================"

echo ""
echo "1. ✅ Checking Beast Mode DNA presence..."
if [ -f ".kiro/BEAST_MODE_DNA.md" ]; then
    echo "   ✅ Beast Mode DNA found"
    echo "   📊 DNA size: $(wc -l < .kiro/BEAST_MODE_DNA.md) lines"
else
    echo "   ❌ Beast Mode DNA not found"
    exit 1
fi

echo ""
echo "2. ✅ Checking systematic steering rules..."
if [ -d ".kiro/steering" ]; then
    echo "   ✅ Steering directory found"
    echo "   📋 Steering files: $(ls .kiro/steering/ | wc -l)"
    ls .kiro/steering/
else
    echo "   ❌ Steering directory not found"
fi

echo ""
echo "3. ✅ Checking deployment capabilities..."
if [ -f "scripts/deploy-autopilot.sh" ]; then
    echo "   ✅ GKE Autopilot deployment script found"
    echo "   🚀 Script is executable: $(test -x scripts/deploy-autopilot.sh && echo 'Yes' || echo 'No')"
else
    echo "   ❌ Deployment script not found"
fi

echo ""
echo "4. ✅ Checking systematic project structure..."
EXPECTED_DIRS=("deployment" "scripts" ".kiro" "src" "tests")
for dir in "${EXPECTED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "   ✅ $dir/ directory present"
    else
        echo "   ⚠️  $dir/ directory missing"
    fi
done

echo ""
echo "🎯 DNA Consumption Test Questions for Fresh Kiro Instance:"
echo "========================================================="
echo ""
echo "Ask the fresh Kiro instance these questions to validate spore assimilation:"
echo ""
echo "Q1: What is GKE Autopilot and how does it differ from standard GKE?"
echo "Q2: What are the systematic principles embedded in this repository?"
echo "Q3: How would you deploy an application using the provided framework?"
echo "Q4: What makes this approach superior to ad-hoc deployment methods?"
echo "Q5: How would you optimize this for a hackathon demonstration?"
echo ""
echo "Expected: Kiro should demonstrate systematic understanding and provide"
echo "comprehensive answers showing Beast Mode DNA assimilation success."
echo ""
echo "🧬 Beast Mode DNA Validation Complete!"
