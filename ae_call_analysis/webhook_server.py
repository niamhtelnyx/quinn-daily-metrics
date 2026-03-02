#!/usr/bin/env python3
"""
Fellow Call Intelligence Webhook Server
FastAPI endpoint for Fellow → Zapier → Enhanced Call Intelligence Pipeline
"""

import asyncio
import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from pydantic import BaseModel, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Fellow Call Intelligence Webhook",
    description="Webhook endpoint for triggering enhanced call intelligence pipeline",
    version="1.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration
FELLOW_WEBHOOK_SECRET = "fellow_webhook_secret_2026"  # In production, use environment variable
SLACK_CHANNEL = "C38URQASH"  # #bot-testing
MAX_PROCESSING_TIME = 300  # 5 minutes
VALID_EVENT_TYPES = {"call.completed", "call.transcription_ready"}

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class FellowCallMetadata(BaseModel):
    duration_minutes: Optional[int] = None
    participant_count: Optional[int] = None
    fellow_workspace: Optional[str] = None

class FellowCallWebhook(BaseModel):
    call_id: str
    event_name: str
    call_title: str
    timestamp: str
    metadata: Optional[FellowCallMetadata] = None
    
    @validator('call_id')
    def validate_call_id(cls, v):
        if not v or len(v) < 5:
            raise ValueError('call_id must be valid Fellow call identifier')
        return v
    
    @validator('event_name')
    def validate_event_name(cls, v):
        if v not in VALID_EVENT_TYPES:
            raise ValueError(f'event_name must be one of: {VALID_EVENT_TYPES}')
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('timestamp must be valid ISO format')

class WebhookResponse(BaseModel):
    status: str
    message: str
    processing_id: str
    estimated_completion: str
    webhook_id: str
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

# In-memory processing status (in production, use Redis/database)
processing_status: Dict[str, Dict[str, Any]] = {}

def verify_webhook_signature(payload: bytes, signature: str, timestamp: str) -> bool:
    """Verify webhook signature using HMAC-SHA256"""
    try:
        # Check timestamp (prevent replay attacks)
        request_time = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - request_time) > 300:  # 5 minutes tolerance
            return False
        
        # Verify signature
        expected_signature = hmac.new(
            FELLOW_WEBHOOK_SECRET.encode(),
            f"{timestamp}.{payload.decode()}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception:
        return False

async def process_fellow_call_intelligence(
    call_id: str, 
    call_title: str, 
    processing_id: str,
    metadata: Optional[FellowCallMetadata] = None
):
    """Background task: Complete enhanced call intelligence pipeline"""
    
    logger.info(f"Starting call intelligence processing for {call_id}")
    
    # Update processing status
    processing_status[processing_id] = {
        "status": "processing",
        "current_step": "initializing",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "call_id": call_id
    }
    
    try:
        # Step 1: Fellow API - Get call details
        logger.info(f"Step 1: Fetching Fellow call data for {call_id}")
        processing_status[processing_id]["current_step"] = "fellow_api"
        
        # Import our existing enhanced pipeline components
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        # TODO: Import actual pipeline components
        # from enhanced_call_processor import process_call_with_intelligence
        # from company_intelligence_integration import CompanyIntelligenceIntegration
        # from salesforce_event_updater import SalesforceEventUpdater
        
        # Simulate the complete pipeline for now
        await asyncio.sleep(2)  # Simulate Fellow API call
        
        # Step 2: Salesforce Event Lookup
        logger.info(f"Step 2: Salesforce event lookup for {call_title}")
        processing_status[processing_id]["current_step"] = "salesforce_lookup"
        await asyncio.sleep(3)  # Simulate Salesforce queries
        
        # Step 3: Company Intelligence Research
        logger.info(f"Step 3: Company intelligence research")
        processing_status[processing_id]["current_step"] = "company_research" 
        await asyncio.sleep(2)  # Simulate company research
        
        # Step 4: OpenAI Analysis
        logger.info(f"Step 4: OpenAI call intelligence analysis")
        processing_status[processing_id]["current_step"] = "openai_analysis"
        await asyncio.sleep(4)  # Simulate OpenAI analysis
        
        # Step 5: Enhanced Message Generation
        logger.info(f"Step 5: Enhanced message format generation")
        processing_status[processing_id]["current_step"] = "message_generation"
        await asyncio.sleep(1)  # Simulate message formatting
        
        # Step 6: Salesforce Event Update
        logger.info(f"Step 6: Updating Salesforce event record")
        processing_status[processing_id]["current_step"] = "salesforce_update"
        await asyncio.sleep(2)  # Simulate Salesforce update
        
        # Step 7: Slack Deployment
        logger.info(f"Step 7: Deploying to Slack channel {SLACK_CHANNEL}")
        processing_status[processing_id]["current_step"] = "slack_deployment"
        
        # TODO: Implement actual Slack deployment
        # slack_result = deploy_to_slack(enhanced_message, SLACK_CHANNEL)
        slack_result = {"message_id": "1234567890.123456"}  # Simulated
        
        await asyncio.sleep(1)  # Simulate Slack API call
        
        # Complete processing
        processing_status[processing_id].update({
            "status": "completed",
            "current_step": "finished",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "slack_message_id": slack_result.get("message_id"),
            "processing_duration_seconds": 15  # Simulated
        })
        
        logger.info(f"✅ Call intelligence processing completed for {call_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing call {call_id}: {str(e)}")
        processing_status[processing_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now(timezone.utc).isoformat()
        })

@app.post("/webhook/fellow-call-intelligence", response_model=WebhookResponse)
@limiter.limit("10/minute")
async def fellow_call_webhook(
    request: Request,
    payload: FellowCallWebhook,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None),
    x_fellow_signature: Optional[str] = Header(None),
    x_fellow_timestamp: Optional[str] = Header(None)
):
    """
    Webhook endpoint for Fellow call completion events
    Triggers enhanced call intelligence pipeline
    """
    
    # Authentication
    if x_fellow_signature and x_fellow_timestamp:
        # HMAC signature authentication (preferred)
        body = await request.body()
        if not verify_webhook_signature(body, x_fellow_signature, x_fellow_timestamp):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif x_api_key:
        # Simple API key authentication
        if x_api_key != FELLOW_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Generate processing ID
    processing_id = str(uuid.uuid4())
    webhook_id = f"webhook_{int(time.time())}"
    
    # Log webhook receipt
    logger.info(f"📞 Received Fellow webhook: {payload.call_id} - {payload.call_title}")
    
    # Queue background processing
    background_tasks.add_task(
        process_fellow_call_intelligence,
        payload.call_id,
        payload.call_title,
        processing_id,
        payload.metadata
    )
    
    # Immediate response to webhook
    response = WebhookResponse(
        status="accepted",
        message="Call intelligence pipeline initiated",
        processing_id=processing_id,
        estimated_completion="2-3 minutes",
        webhook_id=webhook_id,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    logger.info(f"✅ Webhook accepted, processing ID: {processing_id}")
    return response

@app.get("/webhook/status/{processing_id}")
@limiter.limit("30/minute")
async def get_processing_status(request: Request, processing_id: str):
    """Get processing status for a webhook request"""
    
    if processing_id not in processing_status:
        raise HTTPException(status_code=404, detail="Processing ID not found")
    
    return processing_status[processing_id]

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Fellow Call Intelligence Webhook",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook/fellow-call-intelligence",
            "status": "/webhook/status/{processing_id}", 
            "health": "/health"
        }
    }

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "webhook_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )