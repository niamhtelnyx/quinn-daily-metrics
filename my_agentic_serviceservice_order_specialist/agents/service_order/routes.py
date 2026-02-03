"""Service Order Agent HTTP endpoints.

This module provides REST API endpoints for invoking the Service Order agent,
supporting both synchronous and streaming response modes, plus file uploads.
"""

import json
import uuid
import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from my_agentic_serviceservice_order_specialist.agents.service_order.agent import ServiceOrderAgentBuilder
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.server.dependencies.agents import get_agent

service_order_router = APIRouter(
    prefix=f"/{ServiceOrderAgentBuilder.SLUG}",
    tags=["agents"],
)


class AgentPayload(BaseModel):
    """Request payload for Service Order agent invocation.

    Attributes:
        question: The user's question or task for the agent (1-10000 characters)
        thread_id: Conversation thread ID for persistence (auto-generated if not provided)
    """

    question: str = Field(..., min_length=1, max_length=10000, description="User's question or task")
    thread_id: uuid.UUID | None = Field(None, description="Conversation thread ID")


class AgentResponse(BaseModel):
    """Response from Service Order agent invocation.

    Attributes:
        answer: The agent's complete response
        thread_id: The thread ID used for this conversation
    """

    answer: str = Field(..., description="Agent's response")
    thread_id: uuid.UUID = Field(..., description="Conversation thread ID")


@service_order_router.post("/invoke", response_model=AgentResponse)
async def invoke_service_order_agent(
    payload: AgentPayload,
    agent: Agent = Depends(get_agent(ServiceOrderAgentBuilder)),
) -> AgentResponse:
    """Invoke the Service Order agent with a question or task.

    Args:
        payload: The user's question and optional thread ID
        agent: The Service Order agent instance (injected dependency)

    Returns:
        The agent's response with answer and thread ID

    Raises:
        HTTPException: If the agent execution fails
    """
    try:
        thread_id = str(payload.thread_id) if payload.thread_id else str(uuid.uuid4())
        response = await agent.run(payload.question, thread_id=thread_id)
        
        return AgentResponse(
            answer=response.response,
            thread_id=uuid.UUID(response.thread_id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service Order agent failed: {str(e)}")


@service_order_router.post("/stream")
async def stream_service_order_agent(
    payload: AgentPayload,
    agent: Agent = Depends(get_agent(ServiceOrderAgentBuilder)),
) -> StreamingResponse:
    """Stream responses from the Service Order agent.

    Args:
        payload: The user's question and optional thread ID
        agent: The Service Order agent instance (injected dependency)

    Returns:
        Streaming response with real-time agent output

    Raises:
        HTTPException: If the agent execution fails
    """
    try:
        thread_id = str(payload.thread_id) if payload.thread_id else str(uuid.uuid4())
        
        async def generate_response():
            async for chunk in agent.stream(payload.question, thread_id=thread_id):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service Order streaming failed: {str(e)}")


@service_order_router.post("/upload", response_model=AgentResponse)
async def upload_service_order_pdf(
    file: UploadFile,
    agent: Agent = Depends(get_agent(ServiceOrderAgentBuilder)),
    thread_id: uuid.UUID | None = None,
) -> AgentResponse:
    """Upload and process a Service Order PDF file.

    Args:
        file: Uploaded PDF file
        agent: The Service Order agent instance (injected dependency) 
        thread_id: Optional conversation thread ID

    Returns:
        The agent's response after processing the PDF

    Raises:
        HTTPException: If file processing fails
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process with Service Order agent
            question = f"Please process this Service Order PDF file: {tmp_file_path}"
            thread_id_str = str(thread_id) if thread_id else str(uuid.uuid4())
            response = await agent.run(question, thread_id=thread_id_str)
            
            return AgentResponse(
                answer=response.response,
                thread_id=uuid.UUID(response.thread_id),
            )
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")