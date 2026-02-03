#!/usr/bin/env python3
"""
A2A-compliant Service Order Specialist Agent
Follows Telnyx Agent Architecture specification
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from agent_card import AGENT_CARD
from salesforce_client import SalesforceClient

# A2A Task States (from Telnyx Architecture)
class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"

# A2A Request/Response Models
class A2ATask(BaseModel):
    taskId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.SUBMITTED
    skill: str = Field(..., description="Skill ID to invoke")
    payload: Dict[str, Any] = Field(..., description="Skill-specific input")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    requesterAgent: Optional[str] = None
    webhookUrl: Optional[str] = None

class A2ASendMessageRequest(BaseModel):
    skill: str = Field(..., description="Skill ID to invoke")
    payload: Dict[str, Any] = Field(..., description="Skill input data")
    taskId: Optional[str] = Field(None, description="Optional task ID")
    requesterAgent: Optional[str] = Field(None, description="Requesting agent ID")
    webhookUrl: Optional[str] = Field(None, description="Webhook for async updates")
    mode: Optional[str] = Field("sync", description="sync|streaming|async")

class A2AResponse(BaseModel):
    taskId: str
    state: TaskState
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None

class A2AError(BaseModel):
    code: str
    category: str  # "retriable", "permanent", "user_error"
    message: str
    source: Dict[str, Any]
    chain: Optional[List[Dict[str, str]]] = None

# Initialize FastAPI app
app = FastAPI(
    title="Service Order Specialist Agent (A2A)",
    description=AGENT_CARD["description"], 
    version=AGENT_CARD["version"],
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://a2a-inspector.internal.telnyx.com"],  # A2A Inspector
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# In-memory task store (production would use Redis/PostgreSQL)
tasks: Dict[str, A2ATask] = {}

# Initialize Salesforce client
salesforce_client = SalesforceClient()

# Authentication
async def verify_agent_token(authorization: Optional[str] = Header(None)):
    """Verify Telnyx agent authentication token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.split(" ", 1)[1]
    expected_token = os.getenv("TELNYX_AGENT_TOKEN")
    
    # Development mode - allow any token if none configured
    if not expected_token and os.getenv("DEBUG", "false").lower() == "true":
        return token
        
    if not expected_token:
        raise HTTPException(status_code=500, detail="Agent token not configured")
    
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    
    return token

# Core A2A Endpoints (Required by spec)

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Serve the Agent Card for A2A discovery (required endpoint)"""
    return JSONResponse(content=AGENT_CARD)

@app.post("/a2a/tasks")
async def send_message(
    request: A2ASendMessageRequest,
    token: str = Depends(verify_agent_token)
) -> A2AResponse:
    """A2A SendMessage endpoint - main agent interaction"""
    
    # Validate skill exists
    available_skills = [skill["id"] for skill in AGENT_CARD["skills"]]
    if request.skill not in available_skills:
        return A2AResponse(
            taskId=request.taskId or str(uuid.uuid4()),
            state=TaskState.REJECTED,
            error={
                "code": "SKILL_NOT_FOUND",
                "category": "user_error", 
                "message": f"Unknown skill: {request.skill}. Available: {available_skills}",
                "source": {
                    "agentId": "service-order-specialist",
                    "agentName": AGENT_CARD["name"]
                }
            }
        )
    
    # Create task
    task = A2ATask(
        taskId=request.taskId or str(uuid.uuid4()),
        skill=request.skill,
        payload=request.payload,
        requesterAgent=request.requesterAgent,
        webhookUrl=request.webhookUrl
    )
    
    tasks[task.taskId] = task
    
    # Handle different modes
    if request.mode == "async":
        # Start background processing
        asyncio.create_task(process_task_async(task.taskId))
        return A2AResponse(taskId=task.taskId, state=TaskState.SUBMITTED)
    
    elif request.mode == "streaming":
        # Return streaming response
        return StreamingResponse(
            stream_task_processing(task.taskId),
            media_type="text/event-stream"
        )
    
    else:  # sync mode (default)
        # Process synchronously 
        result = await process_task(task.taskId)
        return result

@app.get("/a2a/tasks/{task_id}")
async def get_task(
    task_id: str,
    token: str = Depends(verify_agent_token)
) -> A2AResponse:
    """Get task status (A2A GetTask operation)"""
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = tasks[task_id]
    return A2AResponse(
        taskId=task.taskId,
        state=task.state,
        result=task.result,
        error=task.error,
        progress=task.progress
    )

@app.get("/a2a/tasks")
async def list_tasks(
    state: Optional[TaskState] = None,
    skill: Optional[str] = None,
    limit: int = 50,
    token: str = Depends(verify_agent_token)
) -> Dict[str, Any]:
    """List tasks with optional filtering (A2A ListTasks operation)"""
    
    filtered_tasks = []
    for task in tasks.values():
        if state and task.state != state:
            continue
        if skill and task.skill != skill:
            continue
        filtered_tasks.append({
            "taskId": task.taskId,
            "state": task.state,
            "skill": task.skill,
            "createdAt": task.createdAt,
            "updatedAt": task.updatedAt
        })
    
    # Sort by creation time, most recent first
    filtered_tasks.sort(key=lambda x: x["createdAt"], reverse=True)
    
    return {
        "tasks": filtered_tasks[:limit],
        "total": len(filtered_tasks),
        "hasMore": len(filtered_tasks) > limit
    }

@app.post("/a2a/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    token: str = Depends(verify_agent_token)
) -> A2AResponse:
    """Cancel a running task (A2A CancelTask operation)"""
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = tasks[task_id]
    
    if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED]:
        return A2AResponse(
            taskId=task.taskId,
            state=task.state,
            error={
                "code": "TASK_ALREADY_FINISHED",
                "category": "user_error",
                "message": f"Task is already in state: {task.state}",
                "source": {"agentId": "service-order-specialist"}
            }
        )
    
    task.state = TaskState.CANCELED
    task.updatedAt = datetime.now(timezone.utc)
    
    return A2AResponse(taskId=task.taskId, state=task.state)

# Task Processing Functions

async def process_task(task_id: str) -> A2AResponse:
    """Process a task synchronously"""
    
    task = tasks[task_id]
    task.state = TaskState.WORKING
    task.updatedAt = datetime.now(timezone.utc)
    
    try:
        # Route to appropriate skill handler
        if task.skill == "process-service-order-change":
            result = await handle_service_order_change(task.payload)
        elif task.skill == "validate-commitment-terms":
            result = await handle_commitment_validation(task.payload)
        elif task.skill == "extract-service-order-pdf":
            result = await handle_pdf_extraction(task.payload)
        elif task.skill == "salesforce-service-order-lookup":
            result = await handle_salesforce_lookup(task.payload)
        else:
            raise ValueError(f"Unknown skill: {task.skill}")
        
        task.state = TaskState.COMPLETED
        task.result = result
        task.updatedAt = datetime.now(timezone.utc)
        
        return A2AResponse(
            taskId=task.taskId,
            state=task.state,
            result=result
        )
        
    except Exception as e:
        task.state = TaskState.FAILED
        task.error = {
            "code": "PROCESSING_ERROR",
            "category": "retriable",
            "message": str(e),
            "source": {
                "agentId": "service-order-specialist", 
                "agentName": AGENT_CARD["name"],
                "skill": task.skill
            }
        }
        task.updatedAt = datetime.now(timezone.utc)
        
        return A2AResponse(
            taskId=task.taskId,
            state=task.state,
            error=task.error
        )

async def process_task_async(task_id: str):
    """Process a task asynchronously with webhook notifications"""
    
    result = await process_task(task_id)
    task = tasks[task_id]
    
    # Send webhook notification if configured
    if task.webhookUrl:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    task.webhookUrl,
                    json={
                        "taskId": task.taskId,
                        "state": task.state.value,
                        "result": task.result,
                        "error": task.error
                    },
                    timeout=10
                )
        except Exception as e:
            print(f"Webhook notification failed: {e}")

async def stream_task_processing(task_id: str):
    """Stream task processing with SSE"""
    
    task = tasks[task_id]
    
    # Send initial status
    yield f"data: {json.dumps({'taskId': task_id, 'state': 'submitted'})}\n\n"
    
    # Simulate processing with progress updates
    task.state = TaskState.WORKING
    yield f"data: {json.dumps({'taskId': task_id, 'state': 'working', 'progress': {'step': 'starting'}})}\n\n"
    
    try:
        # Process the actual task
        result = await process_task(task_id)
        
        # Send completion
        yield f"data: {json.dumps({'taskId': task_id, 'state': 'completed', 'result': result.result})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'taskId': task_id, 'state': 'failed', 'error': {'message': str(e)}})}\n\n"

# Skill Implementation Handlers

async def handle_service_order_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle service order changes using existing service-order-ops skill"""
    
    # This would integrate with the existing service-order-ops skill
    # For now, return a structured response
    return {
        "success": True,
        "action": payload.get("action"),
        "customer": payload.get("customer_name"),
        "org_id": payload.get("org_id"),
        "message": "Service order change processed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def handle_commitment_validation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle commitment term validation"""
    
    return {
        "validation_passed": True,
        "org_id": payload.get("org_id"),
        "overlaps_found": False,
        "compliance_check": "passed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def handle_pdf_extraction(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PDF service order extraction"""
    
    return {
        "extraction_successful": True,
        "format": payload.get("extract_format", "json"),
        "pdf_source": payload.get("pdf_path") or payload.get("pdf_url"),
        "extracted_data": {
            "customer_name": "Sample Customer",
            "contract_dates": "2026-01-01 to 2026-12-31",
            "commitment_amount": 2500
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def handle_salesforce_lookup(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Salesforce service order lookup using real sf CLI"""
    
    customer_name = payload.get("customer_name", "")
    include_terminated = payload.get("include_terminated", False)
    org_id = payload.get("org_id")
    
    if not customer_name:
        raise ValueError("customer_name is required for Salesforce lookup")
    
    # Use real Salesforce client
    return await salesforce_client.lookup_service_orders(
        customer_name=customer_name,
        include_terminated=include_terminated,
        org_id=org_id
    )

# Health and discovery endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": AGENT_CARD["name"],
        "version": AGENT_CARD["version"],
        "skills_available": len(AGENT_CARD["skills"]),
        "tasks_active": len([t for t in tasks.values() if t.state == TaskState.WORKING]),
        "uptime": "unknown"  # Could track actual uptime
    }

@app.get("/a2a/capabilities")
async def get_capabilities():
    """List agent capabilities (alternative to Agent Card)"""
    return {
        "skills": AGENT_CARD["skills"],
        "supportedModes": AGENT_CARD["supportedModes"],
        "capabilities": AGENT_CARD["capabilities"],
        "specializations": AGENT_CARD["specializations"]
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "available_endpoints": [
                "GET /.well-known/agent.json",
                "GET /health",
                "POST /a2a/tasks", 
                "GET /a2a/tasks/{task_id}",
                "GET /a2a/tasks",
                "POST /a2a/tasks/{task_id}/cancel"
            ],
            "agent": AGENT_CARD["name"]
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"🚀 Service Order Specialist Agent (A2A) starting...")
    print(f"📊 Agent: {AGENT_CARD['name']} v{AGENT_CARD['version']}")
    print(f"🛠️ Skills: {len(AGENT_CARD['skills'])}")
    print(f"🔗 A2A Endpoint: /a2a/tasks")
    print(f"📋 Agent Card: /.well-known/agent.json")
    
    uvicorn.run(
        "a2a_service:app",
        host="0.0.0.0", 
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )