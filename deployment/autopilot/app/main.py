#!/usr/bin/env python3
"""
GKE Autopilot AI Microservice
Hackathon-ready FastAPI application with AI agent capabilities
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    cluster_type: str = "GKE Autopilot"

class AIAgentRequest(BaseModel):
    task: str
    parameters: Optional[Dict] = {}

class AIAgentResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict] = None
    processing_time: float

class MetricsResponse(BaseModel):
    requests_processed: int
    average_response_time: float
    active_tasks: int
    cluster_info: Dict

# Global state (in production, use Redis or similar)
app_state = {
    "requests_processed": 0,
    "total_response_time": 0.0,
    "active_tasks": 0,
    "start_time": datetime.now()
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 GKE Autopilot AI Microservice starting up...")
    logger.info(f"🧬 Running on GKE Autopilot cluster")
    yield
    logger.info("🛑 GKE Autopilot AI Microservice shutting down...")

# Create FastAPI app
app = FastAPI(
    title="GKE Autopilot AI Microservice",
    description="Hackathon AI microservice running on GKE Autopilot",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with basic info"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        cluster_type="GKE Autopilot"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        cluster_type="GKE Autopilot"
    )

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Application metrics for monitoring"""
    uptime = (datetime.now() - app_state["start_time"]).total_seconds()
    avg_response_time = (
        app_state["total_response_time"] / max(app_state["requests_processed"], 1)
    )
    
    return MetricsResponse(
        requests_processed=app_state["requests_processed"],
        average_response_time=avg_response_time,
        active_tasks=app_state["active_tasks"],
        cluster_info={
            "type": "GKE Autopilot",
            "uptime_seconds": uptime,
            "pod_name": os.getenv("HOSTNAME", "unknown"),
            "namespace": os.getenv("NAMESPACE", "hackathon-app")
        }
    )

async def simulate_ai_processing(task: str, parameters: Dict) -> Dict:
    """Simulate AI agent processing"""
    # Simulate processing time based on task complexity
    processing_time = len(task) * 0.1 + len(str(parameters)) * 0.05
    await asyncio.sleep(min(processing_time, 2.0))  # Cap at 2 seconds
    
    # Generate mock AI response
    return {
        "task": task,
        "parameters": parameters,
        "result": f"AI processed: {task}",
        "confidence": 0.95,
        "model": "gke-autopilot-ai-v1",
        "processing_node": os.getenv("HOSTNAME", "unknown")
    }

@app.post("/ai/process", response_model=AIAgentResponse)
async def process_ai_task(request: AIAgentRequest, background_tasks: BackgroundTasks):
    """Process AI task with simulated agent"""
    start_time = datetime.now()
    task_id = f"task_{int(start_time.timestamp())}"
    
    try:
        app_state["active_tasks"] += 1
        
        # Simulate AI processing
        result = await simulate_ai_processing(request.task, request.parameters)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Update metrics
        app_state["requests_processed"] += 1
        app_state["total_response_time"] += processing_time
        app_state["active_tasks"] -= 1
        
        return AIAgentResponse(
            task_id=task_id,
            status="completed",
            result=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        app_state["active_tasks"] -= 1
        logger.error(f"Error processing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/ai/status")
async def get_ai_status():
    """Get AI system status"""
    return {
        "status": "operational",
        "cluster_type": "GKE Autopilot",
        "capabilities": [
            "text_processing",
            "data_analysis", 
            "pattern_recognition",
            "automated_scaling"
        ],
        "performance": {
            "requests_processed": app_state["requests_processed"],
            "active_tasks": app_state["active_tasks"],
            "uptime": (datetime.now() - app_state["start_time"]).total_seconds()
        }
    }

@app.get("/demo")
async def demo_endpoint():
    """Demo endpoint for hackathon presentation"""
    return {
        "message": "🚀 GKE Autopilot AI Microservice Demo",
        "features": [
            "Serverless Kubernetes (zero node management)",
            "Auto-scaling based on demand", 
            "Built-in security and compliance",
            "Pay-per-use pricing model",
            "AI agent simulation capabilities"
        ],
        "hackathon_ready": True,
        "deployment_time": "< 5 minutes",
        "cost_optimization": "automatic",
        "try_it": {
            "health_check": "/health",
            "process_ai_task": "POST /ai/process",
            "view_metrics": "/metrics",
            "ai_status": "/ai/status"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )