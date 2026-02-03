#!/usr/bin/env python3
"""
Web service for Service Order Specialist Agent
Handles HTTP endpoints, A2A communication, and Slack integration
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from agent import ServiceOrderSpecialistAgent, AGENT_CARD

# Initialize FastAPI app
app = FastAPI(
    title="Service Order Specialist Agent",
    description="Specialized agent for Telnyx Service Order operations and commitment management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize the agent
agent = ServiceOrderSpecialistAgent()

# Request/Response Models
class A2ARequest(BaseModel):
    skill: str = Field(..., description="A2A skill identifier")
    payload: Dict[str, Any] = Field(..., description="Skill-specific payload")
    task_id: Optional[str] = Field(None, description="Optional task identifier")
    requester_agent: Optional[str] = Field(None, description="Requesting agent identifier")

class A2AResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")
    task_id: Optional[str] = Field(None, description="Task identifier if provided")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Agent version")
    skills: int = Field(..., description="Number of available A2A skills")
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds")

# Authentication dependency
async def verify_agent_token(authorization: Optional[str] = Header(None)):
    """Verify agent authentication token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.split(" ", 1)[1]
    expected_token = os.getenv("AGENT_TOKEN")
    
    if not expected_token:
        # For development, allow any token if none configured
        if os.getenv("DEBUG", "false").lower() == "true":
            return token
        raise HTTPException(status_code=500, detail="Agent token not configured")
    
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid agent token")
    
    return token

# Endpoints
@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    """Serve the agent card for A2A discovery"""
    return JSONResponse(content=AGENT_CARD)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=AGENT_CARD["version"],
        skills=len(AGENT_CARD["skills"]),
        uptime_seconds=None  # Could track actual uptime
    )

@app.post("/a2a/service-order-specialist/rpc")
async def a2a_rpc_endpoint(
    request: A2ARequest,
    token: str = Depends(verify_agent_token)
) -> A2AResponse:
    """Main A2A RPC endpoint for skill invocation"""
    
    try:
        # Validate skill exists
        available_skills = [skill["id"] for skill in AGENT_CARD["skills"]]
        if request.skill not in available_skills:
            return A2AResponse(
                success=False,
                error=f"Unknown skill: {request.skill}. Available: {available_skills}",
                task_id=request.task_id
            )
        
        # Process the request
        result = await agent.handle_a2a_request(request.skill, request.payload)
        
        return A2AResponse(
            success=result.get("success", True),
            data=result,
            error=result.get("error"),
            task_id=request.task_id
        )
        
    except Exception as e:
        return A2AResponse(
            success=False,
            error=f"Internal error: {str(e)}",
            task_id=request.task_id
        )

@app.post("/slack/events")
async def slack_events_endpoint(payload: Dict[str, Any]):
    """Handle Slack events and interactions"""
    
    # Handle Slack URL verification
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    # Handle Slack events
    event = payload.get("event", {})
    event_type = event.get("type")
    
    if event_type == "message":
        # Process Slack message
        await handle_slack_message(event)
    
    return {"ok": True}

async def handle_slack_message(event: Dict[str, Any]):
    """Process incoming Slack messages"""
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")
    
    # Check if the bot is mentioned
    bot_user_id = os.getenv("SLACK_BOT_USER_ID")
    if bot_user_id and f"<@{bot_user_id}>" in text:
        # This is a message mentioning the bot
        # Process with service order expertise
        
        # Extract the actual message content
        clean_text = text.replace(f"<@{bot_user_id}>", "").strip()
        
        # Determine intent and route to appropriate A2A skill
        if any(keyword in clean_text.lower() for keyword in ["lookup", "find", "search"]):
            skill = "salesforce-service-order-lookup"
        elif any(keyword in clean_text.lower() for keyword in ["update", "change", "modify"]):
            skill = "process-service-order-change"
        elif any(keyword in clean_text.lower() for keyword in ["validate", "check", "verify"]):
            skill = "validate-commitment-terms"
        elif "pdf" in clean_text.lower() or "extract" in clean_text.lower():
            skill = "extract-service-order-pdf"
        else:
            skill = "salesforce-service-order-lookup"  # Default
        
        # Process through A2A
        try:
            result = await agent.handle_a2a_request(skill, {
                "message": clean_text,
                "user": user,
                "channel": channel
            })
            
            # Send response back to Slack
            await send_slack_response(channel, result)
            
        except Exception as e:
            await send_slack_response(channel, {
                "success": False,
                "error": f"Error processing request: {str(e)}"
            })

async def send_slack_response(channel: str, result: Dict[str, Any]):
    """Send response back to Slack channel"""
    # This would use the Slack SDK to send messages
    # Implementation depends on your Slack bot setup
    pass

@app.get("/skills")
async def list_skills():
    """List available A2A skills"""
    return {
        "skills": AGENT_CARD["skills"],
        "total_count": len(AGENT_CARD["skills"])
    }

@app.get("/skills/{skill_id}")
async def get_skill_info(skill_id: str):
    """Get detailed information about a specific skill"""
    for skill in AGENT_CARD["skills"]:
        if skill["id"] == skill_id:
            return skill
    
    raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "available_endpoints": [
                "GET /.well-known/agent-card.json",
                "GET /health", 
                "POST /a2a/service-order-specialist/rpc",
                "POST /slack/events",
                "GET /skills",
                "GET /skills/{skill_id}"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "The service order specialist encountered an error"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    print(f"🚀 Service Order Specialist Agent starting...")
    print(f"📊 Agent Card: {AGENT_CARD['name']} v{AGENT_CARD['version']}")
    print(f"🛠️ Available skills: {len(AGENT_CARD['skills'])}")
    print(f"🔗 A2A Endpoint: /a2a/service-order-specialist/rpc")
    print(f"💬 Slack Endpoint: /slack/events")
    
    # Register with A2A discovery if configured
    discovery_url = os.getenv("A2A_DISCOVERY_URL")
    if discovery_url:
        print(f"📡 Registering with A2A discovery at {discovery_url}")
        # Implementation would register this agent with discovery service

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "web_service:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )