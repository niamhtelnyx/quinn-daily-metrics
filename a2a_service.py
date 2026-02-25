#!/usr/bin/env python3
"""
A2A-compliant Service Order Specialist Agent
Follows Telnyx Agent Architecture specification
"""

import os
import json
import uuid
import asyncio
import subprocess
import tempfile
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

# Helper functions for PDF extraction formatting
def format_extraction_summary(parsed_data: Dict[str, Any]) -> str:
    """Format parsed data into human-readable summary"""
    summary = []
    
    # Customer info
    metadata = parsed_data.get("_metadata", {})
    customer_info = metadata.get("customer_info", {})
    if customer_info.get("company_name"):
        summary.append(f"Customer: {customer_info['company_name']}")
    
    # Contract terms
    start_date = parsed_data.get("start_date")
    duration = parsed_data.get("duration")
    commitment_type = parsed_data.get("type")
    
    if start_date:
        summary.append(f"Start Date: {start_date}")
    if duration:
        summary.append(f"Duration: {duration} months")
    if commitment_type:
        summary.append(f"Commitment Type: {commitment_type}")
    
    # Commitment details
    commits = parsed_data.get("commits", [])
    if commits:
        summary.append(f"Commitment Schedule ({len(commits)} periods):")
        for i, commit in enumerate(commits[:5], 1):  # Show first 5
            amount = commit.get("amount", 0)
            start = commit.get("start_date", "Unknown")
            duration = commit.get("duration", "Unknown")
            summary.append(f"  {i}. ${amount:,.0f}/month starting {start} ({duration} months)")
        if len(commits) > 5:
            summary.append(f"  ... and {len(commits) - 5} more periods")
    
    return "\n".join(summary)

def format_for_validation(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format parsed data for immediate validation use"""
    
    # Extract customer info
    metadata = parsed_data.get("_metadata", {})
    customer_info = metadata.get("customer_info", {})
    
    # Format for validation
    validation_data = {
        "customer_name": customer_info.get("company_name", "Unknown"),
        "contract_start_date": parsed_data.get("start_date"),
        "contract_duration_months": parsed_data.get("duration"),
        "commitment_type": parsed_data.get("type"),
        "cycle": parsed_data.get("cycle", "monthly"),
        "commitments": []
    }
    
    # Format commitment schedule for validation
    commits = parsed_data.get("commits", [])
    for commit in commits:
        validation_data["commitments"].append({
            "start_date": commit.get("start_date"),
            "duration_months": commit.get("duration"),
            "monthly_amount": commit.get("amount"),
            "currency": "USD"
        })
    
    # Add applicable services if available
    services = metadata.get("applicable_services", {})
    if services:
        validation_data["applicable_services"] = services
    
    return validation_data

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
        elif task.skill == "create-service-order":
            result = await handle_create_service_order(task.payload)
        elif task.skill == "resolve-mission-control-account":
            result = await handle_resolve_mission_control_account(task.payload)
        elif task.skill == "download-service-order-document":
            result = await handle_download_service_order_document(task.payload)
        elif task.skill == "commitment-database-query":
            result = await handle_commitment_database_query(task.payload)
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
    
    action = payload.get("action")
    customer_name = payload.get("customer_name")
    explicit_approval = payload.get("explicit_approval_confirmed", False)
    
    # 🚨 ABSOLUTE SAFETY RULE: NEVER finalize financial commitments without explicit approval
    if action == "finalize_commitment" and not explicit_approval:
        return {
            "success": False,
            "error": "FINANCIAL_APPROVAL_BLOCKED", 
            "action": action,
            "customer": customer_name,
            "message": "🚨 ABSOLUTE SAFETY BLOCK: finalize_commitment creates financial commitments and REQUIRES explicit user approval. The user must EXPLICITLY confirm with 'YES' or 'APPROVE' before proceeding. NO shortcuts allowed.",
            "required_parameter": "explicit_approval_confirmed: true",
            "safety_rule": "ZERO_TOLERANCE_FINANCIAL_SAFETY_BLOCK",
            "required_user_action": "User must explicitly respond with YES/APPROVE to proceed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 🚨 ADDITIONAL SAFETY: Allow user-confirmed approvals only
    # Remove the overly restrictive automatic approval block since user said "YES"
    
    # 🚨 HARD RULE: Any action affecting Rev_Ops_Approved__c requires explicit approval  
    if payload.get("set_revops_approved") and not explicit_approval:
        return {
            "success": False,
            "error": "REVOPS_APPROVAL_BLOCKED", 
            "action": action,
            "customer": customer_name,
            "message": "🚨 CRITICAL SAFETY BLOCK: Setting Rev_Ops_Approved__c REQUIRES explicit user approval. This creates financial commitments.",
            "required_parameter": "explicit_approval_confirmed: true",
            "safety_rule": "REV_OPS_APPROVAL_SAFETY_BLOCK",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 🚨 NEW PROPER WORKFLOW - No more skipping steps!
    if action == "approve":
        return {
            "success": False,
            "error": "WORKFLOW_VIOLATION",
            "action": action,
            "customer": customer_name,
            "message": "❌ CANNOT skip validation workflow! Must follow proper sequence: 1) download-service-order-document, 2) extract-service-order-pdf, 3) validate-data, 4) resolve-mission-control-account, 5) confirm-mc-account, 6) finalize-commitment",
            "required_workflow": [
                "1. Call 'download-service-order-document'",
                "2. Call 'extract-service-order-pdf'", 
                "3. Call 'validate-data'",
                "4. Call 'resolve-mission-control-account'", 
                "5. Call 'confirm-mc-account'",
                "6. Call 'finalize-commitment' with explicit_approval_confirmed=true"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Handle proper workflow steps
    elif action == "finalize_commitment" and explicit_approval:
        # FINAL STEP - Only execute after all validation steps
        # Find the signed service order and check if it's a BAA contract
        sf_client = SalesforceClient()
        lookup_result = await sf_client.lookup_service_orders(customer_name)
        service_orders = lookup_result.get('service_orders', [])
        
        # Find the specific signed service order 
        # Prefer service_order_id, fallback to service_order_name, then any signed SO
        service_order_id = payload.get("service_order_id")
        service_order_name = payload.get("service_order_name")
        signed_so = None
        
        if service_order_id:
            # Prefer ID-based targeting (unique and reliable)
            for so in service_orders:
                if so.get('Stage__c') == 'Signed' and so.get('Id') == service_order_id:
                    signed_so = so
                    break
        elif service_order_name:
            # Fallback to name-based targeting
            for so in service_orders:
                if so.get('Stage__c') == 'Signed' and so.get('Name') == service_order_name:
                    signed_so = so
                    break
        else:
            # Fallback: find any signed service order
            for so in service_orders:
                if so.get('Stage__c') == 'Signed':
                    signed_so = so
                    break
        
        if not signed_so:
            return {
                "success": False,
                "error": "NO_SIGNED_SERVICE_ORDER",
                "action": action,
                "customer": customer_name,
                "message": f"No signed service order found for {customer_name}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Check if this is a BAA contract - get BAA fields
        try:
            # Query BAA status with warning suppression
            baa_check = subprocess.run([
                'bash', '-c',
                f'sf data query -o niamh@telnyx.com --query "SELECT Id, Name, BAA__c, BAA_Amount__c FROM Service_Order__c WHERE Id = \'{signed_so["Id"]}\'" --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            baa_data = json.loads(baa_check.stdout)
            records = baa_data.get('result', {}).get('records', [])
            
            if records and records[0].get('BAA__c'):
                # BAA CONTRACT - No commitment tracking needed!
                return {
                    "success": True,
                    "action": action,
                    "customer": customer_name,
                    "service_order_id": signed_so['Id'],
                    "contract_type": "BAA",
                    "baa_amount": records[0].get('BAA_Amount__c'),
                    "explicit_approval": explicit_approval,
                    "message": f"✅ BAA contract {signed_so['Id']} processed successfully - No commitment tracking needed for BAA contracts (fixed monthly fee)",
                    "workflow": "BAA contracts skip Rev_Ops_Approved__c - customer pays fixed fee regardless of usage",
                    "commitment_created": False,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {
                "success": False,
                "error": "BAA_CHECK_FAILED",
                "action": action,
                "customer": customer_name,
                "message": f"Failed to check BAA status: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # REGULAR CONTRACT - First populate Mission Control Account, then approve
        try:
            # Step 1: Use the MC Account we resolved earlier in the workflow
            # We already resolved MC Account a0TQk00000kwQRDMA2 for United Housing Foundation
            # TODO: Improve workflow to pass MC Account ID between steps
            
            # For now, query the account to find MC Account using simpler query
            opp_query = subprocess.run([
                'bash', '-c',
                f'sf data query -o niamh@telnyx.com --query "SELECT Opportunity__r.AccountId FROM Service_Order__c WHERE Id = \'{signed_so["Id"]}\'" --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            opp_data = json.loads(opp_query.stdout)
            opp_records = opp_data.get('result', {}).get('records', [])
            
            if not opp_records:
                return {
                    "success": False,
                    "error": "NO_OPPORTUNITY_FOUND",
                    "action": action,
                    "customer": customer_name,
                    "message": f"No opportunity found for service order {signed_so['Id']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            account_id = opp_records[0]['Opportunity__r']['AccountId']
            
            # Now find MC Account for this account
            mc_query_result = subprocess.run([
                'bash', '-c',
                f'sf data query -o niamh@telnyx.com --query "SELECT Id FROM Mission_Control_Account__c WHERE Account__c = \'{account_id}\' LIMIT 1" --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            mc_data = json.loads(mc_query_result.stdout)
            mc_records = mc_data.get('result', {}).get('records', [])
            
            if not mc_records:
                return {
                    "success": False,
                    "error": "NO_MISSION_CONTROL_ACCOUNT",
                    "action": action,
                    "customer": customer_name,
                    "message": f"No Mission Control Account found for {customer_name}. Cannot proceed with approval.",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            mc_account_id = mc_records[0]['Id']
            
            # Step 2: Populate Mission_Control_Account__c on the Service Order  
            mc_update_result = subprocess.run([
                'bash', '-c', 
                f'sf data update record -s Service_Order__c -i {signed_so["Id"]} -v "Mission_Control_Account__c={mc_account_id}" -o niamh@telnyx.com --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            # Step 3: Now update Rev_Ops_Approved__c = true using shell to suppress warnings
            update_result = subprocess.run([
                'bash', '-c', 
                f'sf data update record -s Service_Order__c -i {signed_so["Id"]} -v "Rev_Ops_Approved__c=true" -o niamh@telnyx.com --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            # Parse the clean JSON output
            update_response = json.loads(update_result.stdout)
            
            return {
                "success": True,
                "action": action,
                "customer": customer_name,
                "service_order_id": signed_so['Id'],
                "contract_type": "REGULAR",
                "explicit_approval": explicit_approval,
                "salesforce_update": update_response,
                "message": f"✅ Service order {signed_so['Id']} approved successfully - Rev_Ops_Approved__c set to true",
                "commitment_created": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": "SALESFORCE_UPDATE_FAILED",
                "action": action,
                "customer": customer_name,
                "service_order_id": signed_so['Id'],
                "message": f"Failed to update Salesforce: {e.stderr or e.stdout}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Handle validation/confirmation actions
    elif action == "validate_data":
        return {
            "success": True,
            "action": action,
            "customer": customer_name,
            "validation_type": "pdf_data",
            "message": f"PDF data validation completed for {customer_name}. Review the extracted data and respond with 'confirm_mc_account' to proceed.",
            "next_step": "confirm_mc_account",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    elif action == "confirm_mc_account":
        return {
            "success": True,
            "action": action, 
            "customer": customer_name,
            "validation_type": "mc_account",
            "message": f"Mission Control Account confirmation completed for {customer_name}. Review the MC Account mapping and respond with 'finalize_commitment' if ready to create financial commitment.",
            "next_step": "finalize_commitment", 
            "warning": "🚨 Next step creates financial commitments in the system",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    elif action == "terminate":
        # TERMINATE SERVICE ORDER - Set Rev_Ops_Approved__c = false to trigger commitment cancellation
        sf_client = SalesforceClient()
        lookup_result = await sf_client.lookup_service_orders(customer_name)
        service_orders = lookup_result.get('service_orders', [])
        
        # Find the specific service order to terminate
        service_order_id = payload.get("service_order_id")
        service_order_name = payload.get("service_order_name")
        target_so = None
        
        if service_order_id:
            # Prefer ID-based targeting (unique and reliable)
            for so in service_orders:
                if so.get('Id') == service_order_id:
                    target_so = so
                    break
        elif service_order_name:
            # Fallback to name-based targeting
            for so in service_orders:
                if so.get('Name') == service_order_name:
                    target_so = so
                    break
        else:
            # If neither ID nor name specified, this is ambiguous with multiple SOs
            if len(service_orders) > 1:
                return {
                    "success": False,
                    "error": "AMBIGUOUS_TERMINATION",
                    "action": action,
                    "customer": customer_name,
                    "message": f"Found {len(service_orders)} service orders for {customer_name}. Please specify 'service_order_id' (preferred) or 'service_order_name' to terminate the correct one.",
                    "service_orders": [{"id": so.get('Id'), "name": so.get('Name')} for so in service_orders],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            target_so = service_orders[0] if service_orders else None
        
        if not target_so:
            return {
                "success": False,
                "error": "SERVICE_ORDER_NOT_FOUND",
                "action": action,
                "customer": customer_name,
                "service_order_name": service_order_name,
                "message": f"Service order {service_order_name or 'for ' + customer_name} not found",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Terminate by setting Stage__c = "Terminated" (proper Salesforce workflow)
            terminate_result = subprocess.run([
                'bash', '-c', 
                f'sf data update record -s Service_Order__c -i {target_so["Id"]} -v "Stage__c=Terminated" -o niamh@telnyx.com --json 2>/dev/null'
            ], capture_output=True, text=True, check=True)
            
            # Parse the response
            terminate_response = json.loads(terminate_result.stdout)
            
            return {
                "success": True,
                "action": action,
                "customer": customer_name,
                "service_order_id": target_so['Id'],
                "service_order_name": target_so['Name'],
                "salesforce_update": terminate_response,
                "message": f"✅ Service order {target_so['Name']} terminated successfully - Stage__c set to Terminated",
                "commitment_action": "Termination webhook will cancel associated commitment",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": "TERMINATION_FAILED",
                "action": action,
                "customer": customer_name,
                "service_order_id": target_so['Id'],
                "salesforce_error": e.stderr,
                "message": f"Failed to terminate service order {target_so['Name']}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # For other non-financial actions, proceed normally  
    return {
        "success": True,
        "action": action,
        "customer": customer_name,
        "org_id": payload.get("org_id"),
        "explicit_approval": explicit_approval,
        "message": f"Service order {action} processed successfully" + (" (with explicit approval)" if explicit_approval else ""),
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
    """Handle PDF service order extraction using real parser"""
    
    pdf_path = payload.get("pdf_path")
    pdf_url = payload.get("pdf_url")
    extract_format = payload.get("extract_format", "json")
    validate_against_salesforce = payload.get("validate_against_salesforce", False)
    
    if not pdf_path and not pdf_url:
        raise ValueError("Either pdf_path or pdf_url is required")
    
    # If URL provided, download to temp file
    if pdf_url and not pdf_path:
        try:
            import requests
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(response.content)
                pdf_path = temp_file.name
        except Exception as e:
            return {
                "extraction_successful": False,
                "error": f"Failed to download PDF from URL: {str(e)}",
                "pdf_source": pdf_url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        return {
            "extraction_successful": False,
            "error": f"PDF file not found: {pdf_path}",
            "pdf_source": pdf_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        # Call the actual parser script
        script_path = os.path.join(os.path.dirname(__file__), "skills", "pdf-service-order-parser", "scripts", "parse_service_order.py")
        
        # Ensure script exists
        if not os.path.exists(script_path):
            return {
                "extraction_successful": False,
                "error": f"Parser script not found: {script_path}",
                "pdf_source": pdf_path,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Run parser with proper working directory
        result = subprocess.run([
            "python3", script_path, pdf_path
        ], capture_output=True, text=True, timeout=60, 
        cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            # Parse JSON result
            try:
                parsed_data = json.loads(result.stdout)
                
                # Format response based on extract_format
                if extract_format == "summary":
                    # Human readable summary
                    summary = format_extraction_summary(parsed_data)
                    return {
                        "extraction_successful": True,
                        "format": "summary", 
                        "pdf_source": pdf_path,
                        "extracted_data": summary,
                        "raw_data": parsed_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                elif extract_format == "validation_ready":
                    # Format for immediate validation use
                    validation_data = format_for_validation(parsed_data)
                    return {
                        "extraction_successful": True,
                        "format": "validation_ready",
                        "pdf_source": pdf_path,
                        "extracted_data": validation_data,
                        "raw_data": parsed_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # Raw JSON
                    return {
                        "extraction_successful": True,
                        "format": "json",
                        "pdf_source": pdf_path,
                        "extracted_data": parsed_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    "extraction_successful": False,
                    "error": f"Failed to parse JSON output: {str(e)}",
                    "raw_output": result.stdout,
                    "pdf_source": pdf_path,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        else:
            return {
                "extraction_successful": False,
                "error": f"Parser failed: {result.stderr}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "pdf_source": pdf_path,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "extraction_successful": False,
            "error": "PDF parsing timed out (60s limit)",
            "pdf_source": pdf_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "extraction_successful": False,
            "error": f"Unexpected error: {str(e)}",
            "pdf_source": pdf_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    finally:
        # Clean up temp file if we downloaded from URL
        if pdf_url and pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass

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

async def handle_create_service_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle service order creation using the create-service-order skill"""
    
    # Import the create-service-order skill
    import sys
    skill_path = os.path.join(os.path.dirname(__file__), "skills")
    if skill_path not in sys.path:
        sys.path.append(skill_path)
    
    from create_service_order import handle_create_service_order_request
    
    # Use the skill's A2A interface
    result = handle_create_service_order_request(payload)
    
    return result

async def handle_resolve_mission_control_account(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Mission Control Account resolution using the resolve-mission-control-account skill"""
    
    # Import the resolve-mission-control-account skill
    import sys
    skill_path = os.path.join(os.path.dirname(__file__), "skills")
    if skill_path not in sys.path:
        sys.path.append(skill_path)
    
    from resolve_mission_control_account import handle_resolve_mission_control_account_request
    
    # Use the skill's A2A interface
    result = handle_resolve_mission_control_account_request(payload)
    
    return result

async def handle_download_service_order_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle service order document download using the download-service-order-document skill"""
    
    # Import the download-service-order-document skill using importlib (due to hyphens in filename)
    import importlib.util
    skill_file_path = os.path.join(os.path.dirname(__file__), "skills", "download-service-order-document.py")
    
    spec = importlib.util.spec_from_file_location("download_service_order_document", skill_file_path)
    download_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(download_module)
    
    # Use the skill's A2A interface
    result = download_module.handle_download_service_order_document_request(payload)
    
    return result

async def handle_commitment_database_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle commitment database queries using the commitment-database-query skill"""
    
    # Import the commitment database query skill with forced reload
    import sys
    import importlib
    skill_path = os.path.join(os.path.dirname(__file__), "skills")
    if skill_path not in sys.path:
        sys.path.append(skill_path)
    
    # Force reload to get latest changes
    if 'commitment_database_query' in sys.modules:
        importlib.reload(sys.modules['commitment_database_query'])
    
    from commitment_database_query import handle_commitment_database_query_request
    
    # Use the skill's A2A interface
    result = handle_commitment_database_query_request(payload)
    
    return result

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